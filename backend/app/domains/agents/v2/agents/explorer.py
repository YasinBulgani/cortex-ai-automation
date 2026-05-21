"""Explorer Agent — URL → App Map."""
from __future__ import annotations

import logging
from collections import deque
from datetime import datetime
from urllib.parse import urlparse

from ..schemas.app_map import (
    AppMap, ApiObservation, FormDescriptor, FormField, PageNode,
)
from ..state import AgentState
from ..tools.browser import (
    PLAYWRIGHT_AVAILABLE, BrowserSession, BrowserSecurityError, collect_links,
)
from ..tools.locator.snapshot import snapshot_page
from .base import BaseAgent

logger = logging.getLogger(__name__)


_FORMS_JS = r"""
() => {
  const forms = [...document.querySelectorAll('form')];
  return forms.map(f => {
    const fields = [...f.querySelectorAll('input, select, textarea')]
      .filter(el => el.type !== 'hidden')
      .map(el => ({
        name: el.name || null,
        label: (() => {
          if (el.id) {
            const lbl = document.querySelector(`label[for="${el.id}"]`);
            if (lbl) return lbl.innerText.trim();
          }
          return el.closest('label')?.innerText?.trim() || null;
        })(),
        type: el.type || el.tagName.toLowerCase(),
        required: !!el.required,
        placeholder: el.placeholder || null,
        options: el.tagName === 'SELECT' ? [...el.options].map(o => o.value) : [],
      }));
    const submit = f.querySelector('button[type="submit"], input[type="submit"]');
    return {
      form_id: f.id || null,
      form_name: f.getAttribute('name') || null,
      action: f.action || null,
      method: (f.method || 'POST').toUpperCase(),
      fields: fields,
      submit_button: submit ? (submit.innerText || submit.value || 'Submit').trim() : null,
    };
  });
}
"""


class ExplorerAgent(BaseAgent):
    name = "explorer"
    description = "URL'den başlayıp uygulamayı gezer"

    async def execute(self, state: AgentState) -> AgentState:
        payload = state.get("input_payload", {})
        url = payload.get("url")

        if not url:
            state["app_map"] = AppMap(root_url="").to_state_dict()
            return state

        if not PLAYWRIGHT_AVAILABLE:
            logger.warning("Explorer: Playwright yok")
            state["app_map"] = AppMap(root_url=url).to_state_dict()
            return state

        allowlist = self._build_allowlist(url, payload.get("allowed_hosts"))
        max_pages = min(int(payload.get("max_pages", 15)), self.config.max_explorer_pages)
        max_depth = int(payload.get("max_depth", 2))
        credentials = payload.get("credentials")
        t_start = datetime.utcnow()

        try:
            app_map = await self._explore(
                root_url=url, allowlist=allowlist,
                max_pages=max_pages, max_depth=max_depth,
                credentials=credentials,
            )
        except BrowserSecurityError as exc:
            state.setdefault("errors", []).append({
                "agent": self.name, "error": f"Allowlist: {url}",
                "error_type": "BrowserSecurityError",
            })
            state["app_map"] = AppMap(root_url=url).to_state_dict()
            return state
        except Exception as exc:
            logger.exception("Explorer: %s", exc)
            state.setdefault("errors", []).append({
                "agent": self.name, "error": str(exc),
                "error_type": type(exc).__name__,
            })
            state["app_map"] = AppMap(root_url=url).to_state_dict()
            return state

        app_map.explorer_duration_ms = int(
            (datetime.utcnow() - t_start).total_seconds() * 1000
        )
        state["app_map"] = app_map.to_state_dict()
        logger.info(
            "Explorer — pages=%d forms=%d apis=%d",
            app_map.page_count(), app_map.form_count(), len(app_map.apis_observed),
        )
        return state

    async def _explore(
        self,
        *,
        root_url: str,
        allowlist: list[str],
        max_pages: int,
        max_depth: int,
        credentials: dict | None,
    ) -> AppMap:
        app_map = AppMap(root_url=root_url, crawl_depth=max_depth)
        visited: set[str] = set()
        queue: deque[tuple[str, int]] = deque([(root_url, 0)])

        async with BrowserSession(url_allowlist=allowlist) as session:
            if credentials:
                try:
                    login_page = await session.new_page(root_url)
                    await self._attempt_login(login_page, credentials)
                    app_map.auth_required = True
                except Exception as exc:
                    logger.debug("Login deneme fail: %s", exc)

            api_observations: dict[str, ApiObservation] = {}

            while queue and len(app_map.pages) < max_pages:
                current_url, depth = queue.popleft()
                if current_url in visited or depth > max_depth:
                    continue
                visited.add(current_url)

                try:
                    page = await session.new_page(current_url)
                except BrowserSecurityError:
                    continue
                except Exception as exc:
                    logger.debug("Sayfa açılamadı: %s", exc)
                    continue

                self._hook_network(page, api_observations)

                try:
                    snapshot = await snapshot_page(page, wait_timeout_ms=10_000)
                except Exception:
                    snapshot = None

                forms: list[FormDescriptor] = []
                try:
                    raw_forms = await page.evaluate(_FORMS_JS)
                    for rf in raw_forms or []:
                        forms.append(FormDescriptor(
                            page_url=current_url,
                            form_id=rf.get("form_id"),
                            form_name=rf.get("form_name"),
                            action=rf.get("action"),
                            method=(rf.get("method") or "POST").upper(),
                            submit_button=rf.get("submit_button"),
                            fields=[FormField(**f) for f in rf.get("fields", [])],
                        ))
                except Exception:
                    pass

                node = PageNode(
                    url=current_url,
                    title=snapshot.title if snapshot else "",
                    dom_hash=snapshot.hash if snapshot else "",
                    discovered_at=datetime.utcnow(),
                    depth=depth,
                    requires_auth=app_map.auth_required,
                    form_count=len(forms),
                )
                app_map.pages.append(node)
                app_map.forms.extend(forms)

                if depth < max_depth:
                    try:
                        links = await collect_links(page, same_origin_only=True)
                    except Exception:
                        links = []
                    app_map.navigation_graph[current_url] = links
                    for link in links:
                        if link not in visited:
                            queue.append((link, depth + 1))

                try:
                    await page.close()
                except Exception:
                    pass

            app_map.apis_observed = list(api_observations.values())

        return app_map

    def _hook_network(self, page, observations: dict[str, ApiObservation]) -> None:
        def _on_response(resp):
            try:
                url = resp.url
                if not url.startswith("http"):
                    return
                ctype = (resp.headers or {}).get("content-type", "")
                if "json" not in ctype.lower() and "xml" not in ctype.lower():
                    return
                method = resp.request.method
                key = f"{method} {url}"
                if key in observations:
                    observations[key].observed_count += 1
                else:
                    observations[key] = ApiObservation(
                        method=method, url=url,
                        status_code=resp.status,
                        response_content_type=ctype,
                    )
            except Exception:
                pass
        try:
            page.on("response", _on_response)
        except Exception:
            pass

    async def _attempt_login(self, page, credentials: dict) -> None:
        username = credentials.get("username", "")
        password = credentials.get("password", "")
        if not (username and password):
            return
        for sel in ("input[type=email]", "input[name=email]", "input[name=username]", "input[name=user]"):
            try:
                el = page.locator(sel).first
                if await el.count() > 0:
                    await el.fill(username)
                    break
            except Exception:
                continue
        for sel in ("input[type=password]", "input[name=password]"):
            try:
                el = page.locator(sel).first
                if await el.count() > 0:
                    await el.fill(password)
                    break
            except Exception:
                continue
        for sel in ('button[type=submit]', 'input[type=submit]', 'button:has-text("Giriş")', 'button:has-text("Login")'):
            try:
                el = page.locator(sel).first
                if await el.count() > 0:
                    await el.click()
                    await page.wait_for_load_state("networkidle", timeout=15_000)
                    return
            except Exception:
                continue

    def _build_allowlist(self, root_url: str, extras: list[str] | None) -> list[str]:
        host = (urlparse(root_url).hostname or "").lower()
        allow = [host] if host else []
        if extras:
            allow.extend(x.lower() for x in extras)
        try:
            allow.extend(self.config.sandbox_network_allowlist)
        except Exception:
            pass
        return list(set(allow))


_agent = ExplorerAgent()


async def explorer_node(state: AgentState) -> AgentState:
    return await _agent(state)

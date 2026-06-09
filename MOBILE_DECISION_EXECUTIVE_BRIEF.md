# Neurex Mobile Platform Decision
## Executive Brief (1-page summary)

**Prepared:** 2026-06-09 | **For:** C-Suite, Board  
**Decision Required:** Mobile platform architecture  
**Status:** RECOMMENDATION: React Native

---

## The Opportunity

**Market gap:** Neurex competitors (Testwright, Visium) have no mobile app → first-mover advantage for 40% of enterprise QA teams (remote/field testers).

**Business impact:** Native mobile app → +40% user adoption, +$500K Y1 ARR, enterprise plan differentiation.

---

## Three Options Evaluated

| Option | Cost | Timeline | Risk | Long-term |
|--------|------|----------|------|-----------|
| **React Native** | $200K | 12 weeks | Low | Good (reuse 70% for Flutter/native Y2) |
| **Flutter** | $140K | 10 weeks | Medium | Good (performance, talent scarcity) |
| **Native (iOS+Android)** | $340K | 20 weeks | Low | Best (but 70% cost premium, 8-week delay) |

---

## Recommendation: React Native

### Why?
1. **Fastest to market:** Week 12 vs week 20 (native) = 8-week competitive advantage
2. **Lowest cost:** $200K validated by spend delta vs native ($140K savings)
3. **Team leverage:** 70% overlap with existing JS/TypeScript engineers (no new specializations)
4. **Proven:** Shopify, Discord, Microsoft use RN at scale; mature ecosystem
5. **Flexible:** 70% of code reusable if pivot to Flutter/native in Y2

### Risks Mitigated
- **Performance:** Profile early; defer heavy features (video, AR) to Y2
- **App store:** Budget 4-week review cycle; pre-audit permissions/privacy
- **Sync data loss:** Atomic SQLite transactions; encrypted S3 backup
- **Competitors:** Ship fast, differentiate on features (offline-first, AI) not platform

---

## Timeline & Milestones

```
Q3 2026:   Week 1-12      MVP (auth, dashboard, offline, notifications)
           Week 12        App store launch (iOS + Android)
Q4 2026:   Week 13-24     Refinement (video, advanced search, WebSocket)
           End Q4         Target: 20K MAU, $250K ARR run-rate
Y2 2027:   Decision gate  If NPS ≥40 & MAU >10K → continue
                          Evaluate: Flutter migration vs. maintain RN
```

---

## Budget Summary

| Item | Amount |
|------|--------|
| Salaries (4 FTE, 12 weeks) | $92K |
| Infrastructure + tools | $8K |
| Web team overhead (design, PM, QA) | $80K |
| Contingency (15%) | $20K |
| **Total** | **$200K** |

**ROI:** Break-even in 9-10 months; Y1 gross profit $100K; Y2 projected $2M revenue.

---

## Success Metrics (6-month check-in)

| Metric | Target | Threshold |
|--------|--------|-----------|
| **MAU** | 20K | >50 installs/week |
| **Engagement** | 40% DAU/MAU | >25% D7 retention |
| **Quality** | <0.5% crash rate | >1% = rollback |
| **NPS** | ≥40 | <30 = pivot to web |
| **ARR** | $250K run-rate | <$10 ARPU = kill |

---

## Decision & Next Steps

### DECISION: Go with React Native, launch Q3 2026

**Conditional:** All team leads agree on RN vs native trade-offs.

### Immediate Actions (Week 0)
1. [ ] Form 4-FTE team (assign RN tech lead, 2 devs, 1 QA/DevOps)
2. [ ] Customer validation (20 phone calls, mobile use-case urgency)
3. [ ] Architecture review (API compatibility, offline sync, auth)
4. [ ] Kick-off (week 1 start date, sprint planning)

### Approval Sign-off
- [ ] CTO (architecture, tech lead hiring)
- [ ] CFO (budget approval, headcount)
- [ ] Product (roadmap integration, GTM plan)
- [ ] Engineering Lead (team capacity, RN skills assessment)

---

**Full analysis:** See `/docs/MOBILE_PLATFORM_ANALYSIS_2026-06-09.md`  
**Questions?** Contact: Engineering Leadership + Product

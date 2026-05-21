"""
monkey_test_engine.py — Monkey Testing (Exploratory Testing) Engine
Implements random, smart, and hybrid exploration strategies with anomaly detection.
"""
import random
import time
from typing import List, Dict, Optional, Generator
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class MonkeyTestEngine:
    """Performs exploratory testing with multiple strategies."""
    
    def __init__(self):
        """Initialize Monkey Test Engine."""
        self.interactions_performed = []
        self.anomalies_found = []
        self.page_errors = []
    
    def run_monkey_test_streamed(self, page, url: str, mode: str = 'smart',
                                 iterations: int = 50, timeout: int = 30) -> Generator:
        """
        Run monkey testing with streaming progress.
        
        Args:
            page: Playwright page object
            url: URL being tested
            mode: Testing mode (random, smart, hybrid)
            iterations: Number of interactions
            timeout: Session timeout in seconds
        
        Yields:
            Progress updates as JSON-serializable dicts
        """
        start_time = time.time()
        session_id = f"monkey_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        yield {
            'status': 'started',
            'session_id': session_id,
            'url': url,
            'mode': mode,
            'iterations': iterations,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        try:
            # Extract interactive elements
            elements = self._extract_interactive_elements(page)
            
            if not elements:
                yield {
                    'status': 'no_elements',
                    'message': 'No interactive elements found on page'
                }
                return
            
            # Rank elements if in smart or hybrid mode
            if mode in ['smart', 'hybrid']:
                elements = self._rank_elements_by_importance(page, elements)
            
            # Run interactions
            for iteration in range(iterations):
                if time.time() - start_time > timeout:
                    yield {
                        'status': 'timeout',
                        'message': f'Test timeout reached after {iteration} iterations'
                    }
                    break
                
                # Select element based on mode
                element = self._select_element(page, elements, mode)
                
                if not element:
                    continue
                
                # Perform interaction
                interaction_result = self._perform_interaction(page, element)
                
                # Check for anomalies
                anomalies = self._check_for_anomalies(page)
                
                if anomalies:
                    self.anomalies_found.extend(anomalies)
                    yield {
                        'status': 'anomaly_detected',
                        'iteration': iteration + 1,
                        'anomalies': anomalies,
                        'element': element.get('text', element.get('selector')),
                        'timestamp': datetime.utcnow().isoformat()
                    }
                
                self.interactions_performed.append(interaction_result)
                
                # Progress update every 10 iterations
                if (iteration + 1) % 10 == 0:
                    yield {
                        'status': 'progress',
                        'iteration': iteration + 1,
                        'total': iterations,
                        'anomalies_found': len(self.anomalies_found),
                        'timestamp': datetime.utcnow().isoformat()
                    }
                
                # Random delay between interactions
                time.sleep(random.uniform(0.2, 0.8))
            
            # Summary
            duration_ms = int((time.time() - start_time) * 1000)
            yield {
                'status': 'completed',
                'session_id': session_id,
                'total_interactions': len(self.interactions_performed),
                'anomalies_found': len(self.anomalies_found),
                'duration_ms': duration_ms,
                'anomalies': self.anomalies_found,
                'timestamp': datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error in monkey testing: {str(e)}")
            yield {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def _extract_interactive_elements(self, page) -> List[Dict]:
        """Extract all interactive elements from the page."""
        elements = []
        
        try:
            # Buttons
            for button in page.query_selector_all('button'):
                if self._is_visible(button):
                    elements.append({
                        'selector': self._get_selector(button),
                        'type': 'button',
                        'text': button.inner_text() or 'Button',
                        'element': button
                    })
            
            # Links
            for link in page.query_selector_all('a'):
                if self._is_visible(link):
                    elements.append({
                        'selector': self._get_selector(link),
                        'type': 'link',
                        'text': link.inner_text() or 'Link',
                        'element': link
                    })
            
            # Input fields
            for input_field in page.query_selector_all('input:not([type=hidden])'):
                if self._is_visible(input_field):
                    elements.append({
                        'selector': self._get_selector(input_field),
                        'type': 'input',
                        'text': input_field.get_attribute('placeholder') or 'Input',
                        'element': input_field
                    })
            
            # Textareas
            for textarea in page.query_selector_all('textarea'):
                if self._is_visible(textarea):
                    elements.append({
                        'selector': self._get_selector(textarea),
                        'type': 'textarea',
                        'text': 'Text Area',
                        'element': textarea
                    })
            
            # Selects
            for select in page.query_selector_all('select'):
                if self._is_visible(select):
                    elements.append({
                        'selector': self._get_selector(select),
                        'type': 'select',
                        'text': 'Dropdown',
                        'element': select
                    })
        
        except Exception as e:
            logger.warning(f"Error extracting interactive elements: {str(e)}")
        
        return elements
    
    def _rank_elements_by_importance(self, page, elements: List[Dict]) -> List[Dict]:
        """Rank elements by importance for smart testing."""
        for element in elements:
            importance = 0
            
            # Buttons and main actions are important
            if element['type'] == 'button':
                importance += 3
            
            # Input fields are important
            if element['type'] in ['input', 'textarea']:
                importance += 2
            
            # Check if element contains common keywords
            text = element.get('text', '').lower()
            if any(keyword in text for keyword in ['submit', 'search', 'login', 'save', 'delete']):
                importance += 2
            
            element['importance'] = importance
        
        # Sort by importance (descending)
        return sorted(elements, key=lambda x: x.get('importance', 0), reverse=True)
    
    def _select_element(self, page, elements: List[Dict], mode: str):
        """Select an element based on testing mode."""
        if not elements:
            return None
        
        if mode == 'random':
            return random.choice(elements)
        
        elif mode == 'smart':
            # Weighted selection towards high-importance elements
            weights = [max(elem.get('importance', 0), 1) for elem in elements]
            return random.choices(elements, weights=weights)[0]
        
        elif mode == 'hybrid':
            # 70% smart, 30% random
            if random.random() < 0.7:
                weights = [max(elem.get('importance', 0), 1) for elem in elements]
                return random.choices(elements, weights=weights)[0]
            else:
                return random.choice(elements)
        
        return random.choice(elements)
    
    def _perform_interaction(self, page, element: Dict) -> Dict:
        """Perform an interaction on an element."""
        try:
            elem = element['element']
            element_type = element['type']
            
            if element_type == 'button':
                elem.click()
                action = 'clicked'
            
            elif element_type == 'link':
                elem.click()
                action = 'clicked'
            
            elif element_type == 'input':
                elem.click()
                elem.fill(self._generate_random_input())
                action = 'filled'
            
            elif element_type == 'textarea':
                elem.click()
                elem.fill(self._generate_random_input())
                action = 'filled'
            
            elif element_type == 'select':
                options = elem.query_selector_all('option')
                if options:
                    random.choice(options).click()
                action = 'selected'
            
            else:
                action = 'unknown'
            
            return {
                'element_type': element_type,
                'action': action,
                'text': element.get('text'),
                'timestamp': datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            logger.warning(f"Error performing interaction: {str(e)}")
            return {
                'element_type': element.get('type'),
                'action': 'failed',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def _check_for_anomalies(self, page) -> List[Dict]:
        """Check for anomalies like JS errors, network issues, UI changes."""
        anomalies = []
        
        try:
            # Check for JavaScript errors in console
            errors = page.evaluate("""
                () => window.__errors__ || []
            """)
            if errors:
                anomalies.append({
                    'type': 'javascript_error',
                    'details': errors
                })
        
        except:
            pass
        
        # Check for visible error messages
        error_selectors = ['[role=alert]', '.error', '.alert-danger', '[class*=error]']
        for selector in error_selectors:
            try:
                if page.query_selector(selector):
                    text = page.query_selector(selector).inner_text()
                    if text:
                        anomalies.append({
                            'type': 'error_message',
                            'message': text
                        })
                        break
            except:
                pass
        
        return anomalies
    
    def _get_selector(self, element) -> str:
        """Get CSS selector for an element."""
        try:
            return element.evaluate("""
                el => {
                    if (el.id) return `#${el.id}`;
                    if (el.className) return `.${el.className.split(' ')[0]}`;
                    return el.tagName.toLowerCase();
                }
            """)
        except:
            return 'unknown'
    
    def _is_visible(self, element) -> bool:
        """Check if an element is visible."""
        try:
            return element.is_visible()
        except:
            return False
    
    def _generate_random_input(self) -> str:
        """Generate random input for text fields."""
        options = [
            'test@example.com',
            'TestUser123',
            'Random123!',
            'test input',
            'monkey testing',
            '12345',
            '',
        ]
        return random.choice(options)

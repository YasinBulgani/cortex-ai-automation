package recorder;

import java.util.Map;

/**
 * Raw action sent from recorder.js. Plain POJO consumed by Gson.
 *
 * Possible {@code type} values (kept in sync with recorder.js):
 *   navigate, click, fill, change, press, scroll, hover,
 *   assert_visible, assert_text, assert_value, wait, comment
 */
public class RecordedAction {

    public String type;          // see list above
    public Long   timestamp;     // epoch millis
    public String url;           // page URL when the event fired
    public String text;          // input/assert/comment text
    public String key;           // pressed key
    public Integer seconds;      // for wait actions
    public String passwordAlias; // alias suggested by recorder.js for password fields
    public ElementInfo element;  // target element (may be null)

    public static class ElementInfo {
        public String tag;            // input, button, a, ...
        public String id;
        public String name;
        public String type;           // input "type" attribute
        public String value;
        public String placeholder;
        public String role;
        public String ariaLabel;
        public String dataTestId;
        public String dataCy;
        public String dataQa;
        public String text;           // visible text
        public String href;
        public String cssPath;        // CSS path produced by recorder.js
        public String xpath;          // XPath produced by recorder.js
        public Map<String, String> attributes;
        public boolean isPassword;    // input[type=password]
    }
}

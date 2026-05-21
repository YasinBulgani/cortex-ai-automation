
package com.karate.runner;

import com.intuit.karate.junit5.Karate;

public class TestRunner {
    @Karate.Test
    Karate testAll() {
        return Karate.run("classpath:api_tests.feature")
                .tags("@login")
                .relativeTo(getClass());
    }
}

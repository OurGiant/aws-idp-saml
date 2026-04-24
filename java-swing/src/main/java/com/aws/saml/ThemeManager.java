package com.aws.saml;

import com.formdev.flatlaf.FlatDarkLaf;
import com.formdev.flatlaf.FlatLightLaf;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import javax.swing.*;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Theme manager for handling both Swing default LaFs and FlatLaf themes.
 * Provides modern, flat design themes including dark mode.
 */
public class ThemeManager {
    private static final Logger logger = LoggerFactory.getLogger(ThemeManager.class);

    private static final Map<String, ThemeInfo> AVAILABLE_THEMES = new LinkedHashMap<>();

    static {
        // System themes first
        UIManager.LookAndFeelInfo[] lafs = UIManager.getInstalledLookAndFeels();
        for (UIManager.LookAndFeelInfo laf : lafs) {
            AVAILABLE_THEMES.put(laf.getName(), new ThemeInfo(laf.getName(), laf.getClassName(), false));
        }

        // FlatLaf themes - modern flat design
        AVAILABLE_THEMES.put("Flat Light", new ThemeInfo("Flat Light", FlatLightLaf.class.getName(), true));
        AVAILABLE_THEMES.put("Flat Dark", new ThemeInfo("Flat Dark", FlatDarkLaf.class.getName(), true));
    }

    /**
     * Get all available theme names
     */
    public static String[] getAvailableThemeNames() {
        return AVAILABLE_THEMES.keySet().toArray(new String[0]);
    }

    /**
     * Apply the specified theme
     */
    public static boolean applyTheme(String themeName) {
        ThemeInfo themeInfo = AVAILABLE_THEMES.get(themeName);
        if (themeInfo == null) {
            logger.warn("Theme not found: {}", themeName);
            return false;
        }

        try {
            if (themeInfo.isFlatLaf) {
                // FlatLaf themes
                if (themeName.equals("Flat Dark")) {
                    UIManager.setLookAndFeel(new FlatDarkLaf());
                } else if (themeName.equals("Flat Light")) {
                    UIManager.setLookAndFeel(new FlatLightLaf());
                }
            } else {
                // Standard Swing LaF
                UIManager.setLookAndFeel(themeInfo.className);
            }
            logger.info("Applied theme: {}", themeName);
            return true;
        } catch (Exception e) {
            logger.error("Failed to apply theme: {}", themeName, e);
            return false;
        }
    }

    /**
     * Internal theme information class
     */
    private static class ThemeInfo {
        String name;
        String className;
        boolean isFlatLaf;

        ThemeInfo(String name, String className, boolean isFlatLaf) {
            this.name = name;
            this.className = className;
            this.isFlatLaf = isFlatLaf;
        }
    }
}

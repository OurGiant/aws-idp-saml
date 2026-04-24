package com.aws.saml;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import javax.swing.*;
import java.awt.*;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;

/**
 * Configuration dialog for setting application options.
 */
public class ConfigurationDialog extends JDialog {
    private static final Logger logger = LoggerFactory.getLogger(ConfigurationDialog.class);

    private final DatabaseManager databaseManager;
    private final PasswordManager passwordManager;
    private JSpinner durationSpinner;
    private JCheckBox storePasswordCheckBox;
    private JSpinner passwordExpirationSpinner;
    private JComboBox<String> themeComboBox;
    private JButton saveButton;
    private JButton cancelButton;

    public ConfigurationDialog(Frame parent, DatabaseManager databaseManager, PasswordManager passwordManager) {
        super(parent, "Configuration", true);
        this.databaseManager = databaseManager;
        this.passwordManager = passwordManager;

        initializeUI();
        loadCurrentSettings();
        pack();
        setLocationRelativeTo(parent);
    }

    private void initializeUI() {
        setLayout(new BorderLayout());

        // Main panel
        JPanel mainPanel = new JPanel(new GridBagLayout());
        GridBagConstraints gbc = new GridBagConstraints();
        gbc.insets = new Insets(5, 5, 5, 5);
        gbc.anchor = GridBagConstraints.WEST;

        // Session Duration
        gbc.gridx = 0; gbc.gridy = 0;
        mainPanel.add(new JLabel("Session Duration (minutes):"), gbc);

        gbc.gridx = 1;
        durationSpinner = new JSpinner(new SpinnerNumberModel(
            databaseManager.getSessionDuration() / 60, // Convert seconds to minutes
            databaseManager.getMinDuration() / 60,     // Min in minutes
            databaseManager.getMaxDuration() / 60,     // Max in minutes
            15  // Step size in minutes
        ));
        mainPanel.add(durationSpinner, gbc);

        // Store Password Checkbox
        gbc.gridx = 0; gbc.gridy = 1;
        storePasswordCheckBox = new JCheckBox("Store and use Okta password");
        storePasswordCheckBox.addActionListener(e -> updatePasswordExpirationEnabled());
        mainPanel.add(storePasswordCheckBox, gbc);

        // Password Expiration
        gbc.gridx = 0; gbc.gridy = 2;
        mainPanel.add(new JLabel("Password Expiration (minutes):"), gbc);

        gbc.gridx = 1;
        passwordExpirationSpinner = new JSpinner(new SpinnerNumberModel(
            databaseManager.getPasswordExpirationMinutes(),
            15,      // Min 15 minutes
            10080,   // Max 7 days (10080 minutes)
            60       // Step size 1 hour
        ));
        passwordExpirationSpinner.setEnabled(false);
        mainPanel.add(passwordExpirationSpinner, gbc);

        // Theme selection
        gbc.gridx = 0; gbc.gridy = 3;
        mainPanel.add(new JLabel("Theme:"), gbc);

        gbc.gridx = 1;
        themeComboBox = new JComboBox<>();
        String[] themes = ThemeManager.getAvailableThemeNames();
        for (String theme : themes) {
            themeComboBox.addItem(theme);
        }
        mainPanel.add(themeComboBox, gbc);

        add(mainPanel, BorderLayout.CENTER);

        // Button panel
        JPanel buttonPanel = new JPanel(new FlowLayout());
        saveButton = new JButton("Save");
        cancelButton = new JButton("Cancel");

        saveButton.addActionListener(new SaveActionListener());
        cancelButton.addActionListener(e -> setVisible(false));

        buttonPanel.add(saveButton);
        buttonPanel.add(cancelButton);
        add(buttonPanel, BorderLayout.SOUTH);
    }

    private void updatePasswordExpirationEnabled() {
        passwordExpirationSpinner.setEnabled(storePasswordCheckBox.isSelected());
    }

    private void loadCurrentSettings() {
        int currentDurationMinutes = databaseManager.getSessionDuration() / 60;
        durationSpinner.setValue(currentDurationMinutes);

        storePasswordCheckBox.setSelected(databaseManager.getConfig("store_password_enabled") != null &&
                                          databaseManager.getConfig("store_password_enabled").equalsIgnoreCase("true"));
        passwordExpirationSpinner.setValue(databaseManager.getPasswordExpirationMinutes());

        themeComboBox.setSelectedItem(databaseManager.getTheme());

        updatePasswordExpirationEnabled();
    }

    private class SaveActionListener implements ActionListener {
        @Override
        public void actionPerformed(ActionEvent e) {
            try {
                int durationMinutes = (Integer) durationSpinner.getValue();
                int durationSeconds = durationMinutes * 60;
                databaseManager.setSessionDuration(durationSeconds);

                int passwordExpirationMinutes = (Integer) passwordExpirationSpinner.getValue();
                databaseManager.setPasswordExpirationMinutes(passwordExpirationMinutes);

                boolean storePassword = storePasswordCheckBox.isSelected();
                passwordManager.setPasswordStorageEnabled(storePassword);

                String selectedTheme = (String) themeComboBox.getSelectedItem();
                databaseManager.setTheme(selectedTheme);

                logger.info("Configuration saved: session_duration = {} seconds, store_password = {}, password_expiration = {} minutes, theme = {}",
                    durationSeconds, storePassword, passwordExpirationMinutes, selectedTheme);

                // Apply theme immediately
                if (ThemeManager.applyTheme(selectedTheme)) {
                    SwingUtilities.updateComponentTreeUI(getParent());
                } else {
                    logger.warn("Failed to apply theme immediately: {}", selectedTheme);
                }

                JOptionPane.showMessageDialog(ConfigurationDialog.this,
                    "Configuration saved successfully!",
                    "Success",
                    JOptionPane.INFORMATION_MESSAGE);

                setVisible(false);
            } catch (Exception ex) {
                logger.error("Failed to save configuration", ex);
                JOptionPane.showMessageDialog(ConfigurationDialog.this,
                    "Failed to save configuration: " + ex.getMessage(),
                    "Error",
                    JOptionPane.ERROR_MESSAGE);
            }
        }
    }
}
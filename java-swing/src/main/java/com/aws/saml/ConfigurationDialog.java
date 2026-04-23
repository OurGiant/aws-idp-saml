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
    private JSpinner durationSpinner;
    private JButton saveButton;
    private JButton cancelButton;

    public ConfigurationDialog(Frame parent, DatabaseManager databaseManager) {
        super(parent, "Configuration", true);
        this.databaseManager = databaseManager;

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

    private void loadCurrentSettings() {
        int currentDurationMinutes = databaseManager.getSessionDuration() / 60;
        durationSpinner.setValue(currentDurationMinutes);
    }

    private class SaveActionListener implements ActionListener {
        @Override
        public void actionPerformed(ActionEvent e) {
            try {
                int durationMinutes = (Integer) durationSpinner.getValue();
                int durationSeconds = durationMinutes * 60;

                databaseManager.setSessionDuration(durationSeconds);
                logger.info("Configuration saved: session_duration = {} seconds", durationSeconds);

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
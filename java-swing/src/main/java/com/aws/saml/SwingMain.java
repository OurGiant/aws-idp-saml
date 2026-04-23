package com.aws.saml;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import javax.swing.*;
import javax.swing.table.DefaultTableCellRenderer;
import javax.swing.table.DefaultTableModel;
import java.awt.*;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.time.Duration;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Set;
import java.util.TreeSet;

/**
 * Main Swing application for AWS SAML authentication
 */
public class SwingMain extends JFrame {
    private static final Logger logger = LoggerFactory.getLogger(SwingMain.class);

    private JComboBox<String> profileComboBox;
    private JCheckBox useFastPassCheckBox;
    private JButton requestCredentialsButton;
    private JButton showEncryptedButton;
    private JButton showCredentialsButton;

    private DefaultTableModel tokenStatusTableModel;
    private JTable tokenStatusTable;
    private JLabel lastRefreshedLabel;
    private JLabel statusLabel;
    private Timer statusRefreshTimer;

    private ConfigManager configManager;
    private CredentialManager credentialManager;
    private TokenStateManager tokenStateManager;
    private DatabaseManager databaseManager;
    private PasswordManager passwordManager;

    public SwingMain() {
        configManager = new ConfigManager();
        credentialManager = new CredentialManager();
        tokenStateManager = new TokenStateManager();
        databaseManager = new DatabaseManager();
        passwordManager = new PasswordManager(databaseManager);

        initializeUI();
        loadProfiles();
        refreshStatusTable();
        startStatusPolling();
    }

    private void initializeUI() {
        setTitle("AWS IDP SAML Client");
        setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
        setLayout(new BorderLayout());

        setWindowIcon();
        setJMenuBar(createMenuBar());

        // Profile selection panel
        JPanel profilePanel = new JPanel(new FlowLayout());
        profilePanel.add(new JLabel("Select Profile:"));
        profileComboBox = new JComboBox<>();
        profileComboBox.setPreferredSize(new Dimension(220, 25));
        profileComboBox.addActionListener(e -> updateCredentialButtons());
        profilePanel.add(profileComboBox);

        requestCredentialsButton = new JButton("Request Credentials");
        requestCredentialsButton.addActionListener(new RequestCredentialsListener());
        profilePanel.add(requestCredentialsButton);

        useFastPassCheckBox = new JCheckBox("Use Okta FastPass");
        useFastPassCheckBox.setSelected(true);
        profilePanel.add(useFastPassCheckBox);

        showEncryptedButton = new JButton("Encrypted");
        showEncryptedButton.addActionListener(e -> showCredentialsDialog(true, false));
        showEncryptedButton.setEnabled(false); // Initially disabled until credentials are available
        profilePanel.add(showEncryptedButton);

        showCredentialsButton = new JButton("Show Credentials");
        showCredentialsButton.addActionListener(e -> showCredentialsDialog(false, true));
        showCredentialsButton.setEnabled(false); // Initially disabled until credentials are available
        profilePanel.add(showCredentialsButton);

        add(profilePanel, BorderLayout.NORTH);

        // Token status panel
        JPanel tokenStatusPanel = new JPanel(new BorderLayout());
        tokenStatusPanel.setBorder(BorderFactory.createTitledBorder("Credential Status"));

        tokenStatusTableModel = new DefaultTableModel(new String[]{"Profile", "Status", "Expires At", "Time Remaining"}, 0) {
            @Override
            public boolean isCellEditable(int row, int column) {
                return false;
            }
        };

        tokenStatusTable = new JTable(tokenStatusTableModel);
        tokenStatusTable.setFillsViewportHeight(true);
        tokenStatusTable.setRowHeight(26);
        tokenStatusTable.getColumnModel().getColumn(1).setCellRenderer(new StatusTableCellRenderer());

        JScrollPane tableScrollPane = new JScrollPane(tokenStatusTable);
        tokenStatusPanel.add(tableScrollPane, BorderLayout.CENTER);

        JPanel statusControls = new JPanel(new FlowLayout(FlowLayout.RIGHT));
        JButton refreshStatusButton = new JButton("Refresh Status");
        refreshStatusButton.addActionListener(e -> refreshStatusTable());
        statusControls.add(refreshStatusButton);
        lastRefreshedLabel = new JLabel();
        statusControls.add(lastRefreshedLabel);
        tokenStatusPanel.add(statusControls, BorderLayout.SOUTH);

        JPanel centerPanel = new JPanel(new BorderLayout(0, 8));
        centerPanel.add(tokenStatusPanel, BorderLayout.CENTER);

        add(centerPanel, BorderLayout.CENTER);

        JPanel statusPanel = new JPanel(new FlowLayout(FlowLayout.LEFT));
        statusPanel.setBorder(BorderFactory.createLoweredBevelBorder());
        statusLabel = new JLabel("Ready");
        statusPanel.add(statusLabel);
        add(statusPanel, BorderLayout.SOUTH);

        pack();
        setLocationRelativeTo(null);
    }

    private JMenuBar createMenuBar() {
        JMenuBar menuBar = new JMenuBar();
        JMenu fileMenu = new JMenu("File");

        JMenuItem configMenuItem = new JMenuItem("Configuration...");
        configMenuItem.addActionListener(e -> showConfigurationDialog());
        fileMenu.add(configMenuItem);

        fileMenu.addSeparator();

        JMenuItem exitMenuItem = new JMenuItem("Exit");
        exitMenuItem.addActionListener(e -> System.exit(0));
        fileMenu.add(exitMenuItem);

        menuBar.add(fileMenu);
        return menuBar;
    }

    private void setWindowIcon() {
        try {
            ImageIcon icon = new ImageIcon(getClass().getResource("/saml_swing_icon_small.png"));
            if (icon.getImage() != null) {
                setIconImage(icon.getImage());
            }
        } catch (Exception ignore) {
            // Icon is optional and may not be available during development
        }
    }

    private void startStatusPolling() {
        statusRefreshTimer = new Timer(30000, e -> refreshStatusTable());
        statusRefreshTimer.setRepeats(true);
        statusRefreshTimer.start();
    }

    private void refreshStatusTable() {
        try {
            tokenStatusTableModel.setRowCount(0);
            Set<String> profileSet = new TreeSet<>();
            profileSet.addAll(configManager.getAvailableProfiles());
            profileSet.addAll(tokenStateManager.getAllExpirations().keySet());
            profileSet.addAll(credentialManager.getAllProfileNames());

            List<TokenStatusRow> rows = new ArrayList<>();
            Instant now = Instant.now();

            for (String profile : profileSet) {
                Instant expiration = tokenStateManager.getExpiration(profile);
                String status;
                String expiresAtText;
                String timeRemaining;

                if (expiration == null) {
                    status = "UNKNOWN";
                    expiresAtText = "N/A";
                    timeRemaining = "Unknown";
                } else if (expiration.isAfter(now)) {
                    status = "VALID";
                    expiresAtText = formatInstant(expiration);
                    timeRemaining = formatDuration(Duration.between(now, expiration));
                } else {
                    status = "EXPIRED";
                    expiresAtText = formatInstant(expiration);
                    timeRemaining = "Expired";
                }

                rows.add(new TokenStatusRow(profile, status, expiresAtText, timeRemaining));
            }

            // Simplified sorting
            rows.sort((a, b) -> {
                int statusOrder = getStatusOrder(a.getStatus()) - getStatusOrder(b.getStatus());
                if (statusOrder != 0) return statusOrder;
                return a.getProfile().compareTo(b.getProfile());
            });

            for (TokenStatusRow row : rows) {
                tokenStatusTableModel.addRow(new Object[]{row.getProfile(), row.getStatus(), row.getExpiresAt(), row.getTimeRemaining()});
            }

            lastRefreshedLabel.setText("Last refreshed: " + LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")));
            statusLabel.setText("Status refreshed.");
        } catch (Exception e) {
            statusLabel.setText("Failed to update status table: " + e.getMessage());
            System.err.println("Status table update failed: " + e.getMessage());
            e.printStackTrace();
        }
    }

    private int getStatusOrder(String status) {
        return switch (status) {
            case "VALID" -> 0;
            case "UNKNOWN" -> 1;
            default -> 2;
        };
    }

    private String formatInstant(Instant instant) {
        if (instant == null) {
            return "N/A";
        }
        try {
            logger.debug("Formatting instant: {} (class: {})", instant, instant.getClass());
            LocalDateTime localDateTime = LocalDateTime.ofInstant(instant, ZoneId.systemDefault());
            logger.debug("Converted to LocalDateTime: {}", localDateTime);
            String formatted = localDateTime.format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"));
            logger.debug("Formatted result: {}", formatted);
            return formatted;
        } catch (Exception e) {
            logger.error("Error formatting instant: {} - {}", instant, e.getMessage(), e);
            return "Invalid Date";
        }
    }

    private String formatDuration(Duration duration) {
        long seconds = duration.getSeconds();
        long hours = seconds / 3600;
        long minutes = (seconds % 3600) / 60;
        long secs = seconds % 60;

        if (hours > 0) {
            return String.format("%dh %02dm", hours, minutes);
        }
        if (minutes > 0) {
            return String.format("%dm %02ds", minutes, secs);
        }
        return String.format("%02ds", secs);
    }

    private void loadProfiles() {
        try {
            List<String> profiles = configManager.getAvailableProfiles();
            profileComboBox.removeAllItems();
            for (String profile : profiles) {
                profileComboBox.addItem(profile);
            }
        } catch (Exception e) {
            JOptionPane.showMessageDialog(this,
                "Error loading profiles: " + e.getMessage(),
                "Configuration Error",
                JOptionPane.ERROR_MESSAGE);
        }
    }

    private class RequestCredentialsListener implements ActionListener {
        @Override
        public void actionPerformed(ActionEvent e) {
            String selectedProfile = (String) profileComboBox.getSelectedItem();
            if (selectedProfile == null) {
                JOptionPane.showMessageDialog(SwingMain.this,
                    "Please select a profile first.",
                    "No Profile Selected",
                    JOptionPane.WARNING_MESSAGE);
                return;
            }

            // Disable button during processing
            requestCredentialsButton.setEnabled(false);
            requestCredentialsButton.setText("Requesting...");

            // Run credential request in background thread
            SwingWorker<Void, Void> worker = new SwingWorker<Void, Void>() {
                @Override
                protected Void doInBackground() throws Exception {
                    SamlAuthenticator authenticator = new SamlAuthenticator();
                    authenticator.requestCredentials(selectedProfile, useFastPassCheckBox.isSelected());
                    return null;
                }

                @Override
                protected void done() {
                    requestCredentialsButton.setEnabled(true);
                    requestCredentialsButton.setText("Request Credentials");

                    try {
                        get(); // Check for exceptions
                        refreshStatusTable();
                        updateCredentialButtons();
                        JOptionPane.showMessageDialog(SwingMain.this,
                            "Credentials successfully obtained for profile: " + selectedProfile,
                            "Success",
                            JOptionPane.INFORMATION_MESSAGE);
                    } catch (Exception ex) {
                        JOptionPane.showMessageDialog(SwingMain.this,
                            "Error obtaining credentials: " + ex.getMessage(),
                            "Authentication Error",
                            JOptionPane.ERROR_MESSAGE);
                    }
                }
            };
            worker.execute();
        }
    }

    private static class StatusTableCellRenderer extends DefaultTableCellRenderer {
        @Override
        public Component getTableCellRendererComponent(JTable table, Object value, boolean isSelected,
                                                       boolean hasFocus, int row, int column) {
            Component component = super.getTableCellRendererComponent(table, value, isSelected, hasFocus, row, column);
            if (column == 1 && value instanceof String status) {
                switch (status) {
                    case "VALID" -> component.setForeground(new Color(0, 128, 0));
                    case "EXPIRED" -> component.setForeground(Color.RED);
                    default -> component.setForeground(Color.GRAY);
                }
            } else {
                component.setForeground(isSelected ? table.getSelectionForeground() : table.getForeground());
            }
            return component;
        }
    }

    private void showConfigurationDialog() {
        ConfigurationDialog dialog = new ConfigurationDialog(this, databaseManager, passwordManager);
        dialog.setVisible(true);
    }

    private void showCredentialsDialog(boolean showEncrypted, boolean showPlaintext) {
        String selectedProfile = (String) profileComboBox.getSelectedItem();
        if (selectedProfile == null) {
            JOptionPane.showMessageDialog(this,
                "Please select a profile first.",
                "No Profile Selected",
                JOptionPane.WARNING_MESSAGE);
            return;
        }

        CredentialManager.AwsCredentials credentials = credentialManager.getCredentials(selectedProfile);
        if (credentials == null) {
            JOptionPane.showMessageDialog(this,
                "No credentials found for profile: " + selectedProfile,
                "No Credentials",
                JOptionPane.WARNING_MESSAGE);
            return;
        }

        CredentialsDialog dialog = new CredentialsDialog(this, credentials, showEncrypted, showPlaintext);
        dialog.setVisible(true);
    }

    private void updateCredentialButtons() {
        String selectedProfile = (String) profileComboBox.getSelectedItem();
        boolean hasCredentials = selectedProfile != null &&
                                credentialManager.getCredentials(selectedProfile) != null;

        // Check if public key exists for encrypted credentials
        java.nio.file.Path publicKeyPath = java.nio.file.Paths.get(System.getProperty("user.home"), ".aws", "public_key.pem");
        boolean hasPublicKey = java.nio.file.Files.exists(publicKeyPath);

        showEncryptedButton.setEnabled(hasCredentials && hasPublicKey);
        showCredentialsButton.setEnabled(hasCredentials);
    }

    private static class TokenStatusRow {
        private final String profile;
        private final String status;
        private final String expiresAt;
        private final String timeRemaining;

        public TokenStatusRow(String profile, String status, String expiresAt, String timeRemaining) {
            this.profile = profile;
            this.status = status;
            this.expiresAt = expiresAt;
            this.timeRemaining = timeRemaining;
        }

        public String getProfile() { return profile; }
        public String getStatus() { return status; }
        public String getExpiresAt() { return expiresAt; }
        public String getTimeRemaining() { return timeRemaining; }
    }

    public static void main(String[] args) {
        SwingUtilities.invokeLater(() -> {
            try {
                UIManager.setLookAndFeel(UIManager.getSystemLookAndFeelClassName());
            } catch (Exception e) {
                // Use default look and feel
            }

            new SwingMain().setVisible(true);
        });
    }
}
package com.aws.saml;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import javax.swing.*;
import java.awt.*;
import java.awt.datatransfer.StringSelection;
import java.awt.datatransfer.Clipboard;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;

/**
 * Dialog for displaying credentials in various formats.
 */
public class CredentialsDialog extends JDialog {
    private static final Logger logger = LoggerFactory.getLogger(CredentialsDialog.class);

    private final CredentialManager.AwsCredentials credentials;
    private final boolean showEncrypted;
    private final boolean showPlaintext;

    public CredentialsDialog(Frame parent, CredentialManager.AwsCredentials credentials,
                           boolean showEncrypted, boolean showPlaintext) {
        super(parent, "AWS Credentials", true);
        this.credentials = credentials;
        this.showEncrypted = showEncrypted;
        this.showPlaintext = showPlaintext;

        initializeUI();
        pack();
        setLocationRelativeTo(parent);
    }

    private void initializeUI() {
        setLayout(new BorderLayout());

        // Main content panel
        JPanel contentPanel = new JPanel();
        contentPanel.setLayout(new BoxLayout(contentPanel, BoxLayout.Y_AXIS));
        contentPanel.setBorder(BorderFactory.createEmptyBorder(10, 10, 10, 10));

        if (showPlaintext) {
            addPlaintextSection(contentPanel);
        }

        if (showEncrypted) {
            addEncryptedSection(contentPanel);
        }

        // Scroll pane for content
        JScrollPane scrollPane = new JScrollPane(contentPanel);
        scrollPane.setPreferredSize(new Dimension(600, 400));
        add(scrollPane, BorderLayout.CENTER);

        // Button panel
        JPanel buttonPanel = new JPanel(new FlowLayout());
        JButton closeButton = new JButton("Close");
        closeButton.addActionListener(e -> setVisible(false));
        buttonPanel.add(closeButton);
        add(buttonPanel, BorderLayout.SOUTH);
    }

    private void addPlaintextSection(JPanel parent) {
        JPanel section = new JPanel(new BorderLayout());
        section.setBorder(BorderFactory.createTitledBorder("Plaintext Credentials (WARNING: Contains sensitive information)"));

        JTextArea textArea = new JTextArea();
        textArea.setFont(new Font(Font.MONOSPACED, Font.PLAIN, 12));
        textArea.setEditable(false);

        StringBuilder sb = new StringBuilder();
        sb.append("⚠️  WARNING: These credentials contain sensitive information\n");
        sb.append("They will appear in shell history and should not be used in production\n\n");
        sb.append("AWS_ACCESS_KEY_ID=").append(credentials.getAccessKeyId()).append("\n");
        sb.append("AWS_SECRET_ACCESS_KEY=").append(credentials.getSecretAccessKey()).append("\n");
        sb.append("AWS_SESSION_TOKEN=").append(credentials.getSessionToken()).append("\n");

        textArea.setText(sb.toString());

        JButton copyButton = new JButton("Copy to Clipboard");
        copyButton.addActionListener(e -> copyToClipboard(textArea.getText()));

        JPanel buttonPanel = new JPanel(new FlowLayout(FlowLayout.LEFT));
        buttonPanel.add(copyButton);

        section.add(new JScrollPane(textArea), BorderLayout.CENTER);
        section.add(buttonPanel, BorderLayout.SOUTH);

        parent.add(section);
        parent.add(Box.createVerticalStrut(10));
    }

    private void addEncryptedSection(JPanel parent) {
        JPanel section = new JPanel(new BorderLayout());
        section.setBorder(BorderFactory.createTitledBorder("Encrypted Credentials"));

        JTextArea textArea = new JTextArea();
        textArea.setFont(new Font(Font.MONOSPACED, Font.PLAIN, 12));
        textArea.setEditable(false);

        try {
            String encrypted = encryptCredentials(
                credentials.getAccessKeyId(),
                credentials.getSecretAccessKey(),
                credentials.getSessionToken()
            );
            textArea.setText(encrypted);
        } catch (Exception e) {
            textArea.setText("Error generating encrypted credentials: " + e.getMessage());
            logger.error("Failed to encrypt credentials", e);
        }

        JButton copyButton = new JButton("Copy to Clipboard");
        copyButton.addActionListener(e -> copyToClipboard(textArea.getText()));

        JPanel buttonPanel = new JPanel(new FlowLayout(FlowLayout.LEFT));
        buttonPanel.add(copyButton);

        section.add(new JScrollPane(textArea), BorderLayout.CENTER);
        section.add(buttonPanel, BorderLayout.SOUTH);

        parent.add(section);
    }

    private String bytesToHex(byte[] bytes) {
        StringBuilder result = new StringBuilder();
        for (byte b : bytes) {
            result.append(String.format("%02x", b));
        }
        return result.toString();
    }

    private void copyToClipboard(String text) {
        try {
            StringSelection selection = new StringSelection(text);
            Clipboard clipboard = Toolkit.getDefaultToolkit().getSystemClipboard();
            clipboard.setContents(selection, selection);

            JOptionPane.showMessageDialog(this,
                "Copied to clipboard!",
                "Success",
                JOptionPane.INFORMATION_MESSAGE);
        } catch (Exception e) {
            logger.error("Failed to copy to clipboard", e);
            JOptionPane.showMessageDialog(this,
                "Failed to copy to clipboard: " + e.getMessage(),
                "Error",
                JOptionPane.ERROR_MESSAGE);
        }
    }

    private String encryptCredentials(String accessKeyId, String secretAccessKey, String sessionToken) {
        // Check if public key exists
        java.nio.file.Path publicKeyPath = java.nio.file.Paths.get(System.getProperty("user.home"), ".aws", "public_key.pem");
        if (!java.nio.file.Files.exists(publicKeyPath)) {
            return "No public key found. Please run keygen.py to generate a public/private key pair.";
        }

        try {
            // Read the public key
            java.security.KeyFactory keyFactory = java.security.KeyFactory.getInstance("RSA");
            java.nio.file.Path keyPath = java.nio.file.Paths.get(System.getProperty("user.home"), ".aws", "public_key.pem");
            byte[] keyBytes = java.nio.file.Files.readAllBytes(keyPath);
            String keyString = new String(keyBytes).replaceAll("-----BEGIN PUBLIC KEY-----", "")
                                                   .replaceAll("-----END PUBLIC KEY-----", "")
                                                   .replaceAll("\\s", "");
            byte[] decodedKey = java.util.Base64.getDecoder().decode(keyString);
            java.security.spec.X509EncodedKeySpec keySpec = new java.security.spec.X509EncodedKeySpec(decodedKey);
            java.security.PublicKey publicKey = keyFactory.generatePublic(keySpec);

            // Create credentials string
            String credentialsString = accessKeyId + "|" + secretAccessKey + "|" + sessionToken;

            // Generate random AES key and IV
            java.security.SecureRandom random = new java.security.SecureRandom();
            byte[] aesKey = new byte[32]; // 256-bit
            random.nextBytes(aesKey);
            byte[] iv = new byte[12]; // 96-bit for GCM
            random.nextBytes(iv);

            // Encrypt credentials with AES-GCM
            javax.crypto.Cipher aesCipher = javax.crypto.Cipher.getInstance("AES/GCM/NoPadding");
            javax.crypto.spec.SecretKeySpec secretKeySpec = new javax.crypto.spec.SecretKeySpec(aesKey, "AES");
            javax.crypto.spec.GCMParameterSpec gcmSpec = new javax.crypto.spec.GCMParameterSpec(128, iv); // 128-bit tag
            aesCipher.init(javax.crypto.Cipher.ENCRYPT_MODE, secretKeySpec, gcmSpec);
            byte[] encryptedCredentials = aesCipher.doFinal(credentialsString.getBytes(java.nio.charset.StandardCharsets.UTF_8));

            // Encrypt AES key with RSA
            javax.crypto.Cipher rsaCipher = javax.crypto.Cipher.getInstance("RSA/ECB/OAEPWithSHA-256AndMGF1Padding");
            rsaCipher.init(javax.crypto.Cipher.ENCRYPT_MODE, publicKey);
            byte[] encryptedAesKey = rsaCipher.doFinal(aesKey);

            // Combine: encrypted_aes_key:iv:encrypted_credentials (all hex encoded)
            return bytesToHex(encryptedAesKey) + ":" + bytesToHex(iv) + ":" + bytesToHex(encryptedCredentials);

        } catch (Exception e) {
            logger.error("Failed to encrypt credentials", e);
            return "Error encrypting credentials: " + e.getMessage();
        }
    }
}
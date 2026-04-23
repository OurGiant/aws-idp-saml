package com.aws.saml;

/**
 * Represents a SAML role parsed from the assertion
 */
public class SamlRole {
    private final String roleArn;
    private final String principalArn;
    private final String accountNumber;
    private final String roleName;

    public SamlRole(String roleArn, String principalArn) {
        this.roleArn = roleArn;
        this.principalArn = principalArn;

        // Parse account number and role name from ARN
        // Format: arn:aws:iam::123456789012:role/RoleName
        String[] arnParts = roleArn.split(":");
        if (arnParts.length >= 6) {
            this.accountNumber = arnParts[4];
            this.roleName = arnParts[5].substring(5); // Remove "role/" prefix
        } else {
            this.accountNumber = "unknown";
            this.roleName = "unknown";
        }
    }

    public String getRoleArn() { return roleArn; }
    public String getPrincipalArn() { return principalArn; }
    public String getAccountNumber() { return accountNumber; }
    public String getRoleName() { return roleName; }

    @Override
    public String toString() {
        return String.format("SamlRole{account=%s, role=%s}", accountNumber, roleName);
    }
}
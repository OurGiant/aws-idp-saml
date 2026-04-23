package com.aws.saml;

import org.apache.commons.codec.binary.Base64;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.NodeList;
import org.xml.sax.InputSource;

import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;
import java.io.StringReader;
import java.util.ArrayList;
import java.util.List;

/**
 * Parses SAML responses and extracts role information
 */
public class SamlParser {
    private static final Logger logger = LoggerFactory.getLogger(SamlParser.class);

    /**
     * Parse roles from base64-encoded SAML response
     */
    public List<SamlRole> parseRolesFromSaml(String samlResponse) throws Exception {
        logger.debug("Parsing SAML response");

        // Decode base64 SAML response
        byte[] decodedBytes = Base64.decodeBase64(samlResponse);
        String decodedSaml = new String(decodedBytes, "UTF-8");

        // Parse XML
        DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
        factory.setNamespaceAware(true);
        DocumentBuilder builder = factory.newDocumentBuilder();
        Document doc = builder.parse(new InputSource(new StringReader(decodedSaml)));

        // Find SAML assertion
        Element assertion = (Element) doc.getElementsByTagNameNS("urn:oasis:names:tc:SAML:2.0:assertion", "Assertion").item(0);
        if (assertion == null) {
            throw new RuntimeException("SAML Assertion not found in response");
        }

        // Find Role attributes
        NodeList attributeNodes = assertion.getElementsByTagNameNS("urn:oasis:names:tc:SAML:2.0:assertion", "Attribute");
        List<SamlRole> roles = new ArrayList<>();

        for (int i = 0; i < attributeNodes.getLength(); i++) {
            Element attribute = (Element) attributeNodes.item(i);
            String attributeName = attribute.getAttribute("Name");

            if ("https://aws.amazon.com/SAML/Attributes/Role".equals(attributeName)) {
                // Process role attribute values
                NodeList valueNodes = attribute.getElementsByTagNameNS("urn:oasis:names:tc:SAML:2.0:assertion", "AttributeValue");

                for (int j = 0; j < valueNodes.getLength(); j++) {
                    Element valueElement = (Element) valueNodes.item(j);
                    String valueText = valueElement.getTextContent();

                    if (valueText != null && valueText.contains("arn:aws:iam:") && valueText.contains(":role/")) {
                        // Split role and principal ARNs
                        String[] arns = valueText.split(",");
                        if (arns.length == 2) {
                            String roleArn = arns[0].trim();
                            String principalArn = arns[1].trim();
                            roles.add(new SamlRole(roleArn, principalArn));
                        }
                    }
                }
            }
        }

        logger.info("Found {} roles in SAML response", roles.size());
        return roles;
    }
}
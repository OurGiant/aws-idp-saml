# coding=utf-8
import base64
import binascii

import defusedxml.ElementTree as ET
from selenium.webdriver.common.by import By
from tabulate import tabulate

from Logging import Logging

log_stream = Logging('saml_select')


def select_role_from_saml_page(driver, gui_name, iam_role, design):
    driver.maximize_window()
    if design == "A":
        x = 0
        saml_accounts = {}
        while x < len(driver.find_elements(By.CLASS_NAME, "saml-account-name")):
            saml_account = str(driver.find_elements(By.CLASS_NAME, "saml-account-name")[x].text)
            saml_account = saml_account.replace('(', '').replace(')', '').replace(':', '')
            saml_account_name = saml_account.split(' ')[1]
            saml_account_token = saml_account.split(' ')[2]
            saml_accounts.update({saml_account_name: saml_account_token})
            x += 1

        requested_account_token = saml_accounts.get(gui_name)

        account_radio_id = iam_role
        account_radio = driver.find_element(By.ID, account_radio_id)
        account_radio.click()
        sign_in_button = driver.find_element(By.ID, "signin_button")
        sign_in_button.click()
    if design == "B":
        # arn:aws:iam::731057057198:role/Fed-Administrator
        account_hyperlink = driver.find_element(By.ID, iam_role)
        account_hyperlink.click()



def get_roles_from_saml_response(saml_response, account_map):
    try:
        decoded_saml_bytes = base64.b64decode(saml_response)
    except binascii.Error as decode_error:
        log_stream.fatal('SAML Response was not an encoded string. Unable to continue')
        log_stream.critical(str(decode_error))
        raise SystemExit(1)
    decoded_saml = decoded_saml_bytes.decode('utf-8')
    root = ET.fromstring(decoded_saml)
    assertion_element = root.find('.//{urn:oasis:names:tc:SAML:2.0:assertion}Assertion')
    # assertion = ET.tostring(assertion_element, encoding='unicode')

    # Extract the AWS role ARN and session token from the assertion
    all_roles = []
    if account_map is None:
        table_object = [['Id', 'Account Number', 'Role Name']]
    else:
        table_object = [['Id', 'Account Number', 'Account Name', 'Role Name']]

    role_id = 0
    for attribute in assertion_element.findall('.//{urn:oasis:names:tc:SAML:2.0:assertion}Attribute'):
        if attribute.get('Name') == 'https://aws.amazon.com/SAML/Attributes/Role':
            for value in attribute.findall('.//{urn:oasis:names:tc:SAML:2.0:assertion}AttributeValue'):
                if 'arn:aws:iam:' in value.text and ':role/' in value.text:
                    principle_arn = str(value.text).split(',', 1)[1]
                    role_arn = str(value.text).split(',', 1)[0]
                    account_number = role_arn.split(':')[4]
                    account_name = account_number
                    role_name = ((role_arn.split(':')[5]).split('/')[1]).split('-', 1)[1]
                    if account_map is None or len(account_map) == 0:
                        table_object.append([role_id, account_number, role_name])
                        use_account_name = False
                    else:
                        use_account_name = True
                        for account in account_map:
                            if account['number'] == account_number:
                                account_name = account['name']
                            # else:
                            #     account_name = account_number
                        table_object.append([role_id, account_number, account_name, role_name])

                    if use_account_name is True:
                        selector_object = {"id": role_id, "arn": role_arn, "account_number": account_number,
                                           "name": role_name, "principle": principle_arn,
                                           "rolename": account_name + '-' + role_name, "account_name": account_name}
                    else:
                        selector_object = {"id": role_id, "arn": role_arn, "account_number": account_number,
                                           "name": role_name, "principle": principle_arn,
                                           "rolename": account_number + '-' + role_name}
                    all_roles.append(selector_object)
                    role_id += 1
    return all_roles, table_object


def select_role_from_text_menu(all_roles, table_object):
    sorted_accounts = sorted(all_roles, key=lambda d: d['account_number'])

    print(tabulate(table_object, headers='firstrow', tablefmt='fancy_grid'))
    while True:
        try:
            selected_role_id: int = int(input('Enter the Id of the role to assume: '))
            selected_role = all_roles[selected_role_id]
            break
        except IndexError:
            log_stream.warning('No such Id')

    return selected_role

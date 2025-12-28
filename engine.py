import requests

# قاموس الباقات المتاحة لخصم فليكس
FLEX_PACKAGES = {
    "637": "فليكس 300", "523": "فليكس 260", "636": "فليكس 150",
    "517": "فليكس 130", "516": "فليكس 100", "522": "فليكس 90",
    "515": "فليكس 70", "514": "فليكس 60", "632": "فليكس 45", "631": "فليكس 40",
}

def get_token(num, pwd):
    url = "https://mobile.vodafone.com.eg/auth/realms/vf-realm/protocol/openid-connect/token"
    payload = {
        'username': num, 'password': pwd, 'grant_type': 'password',
        'client_secret': 'a2ec6fff-0b7f-4aa4-a733-96ceae5c84c3', 'client_id': 'my-vodafone-app'
    }
    headers = {
        'User-Agent': 'okhttp/4.9.3', 'Accept': 'application/json, text/plain, */*',
        'Accept-Encoding': 'gzip', 'x-agent-operatingsystem': 'V12.5.13.0.RJQMIXM',
        'clientId': 'xxx', 'x-agent-device': 'lime', 'x-agent-version': '2024.10.1', 'x-agent-build': '562'
    }
    res = requests.post(url, data=payload, headers=headers, timeout=30)
    if res.status_code == 200:
        return res.json().get('access_token')
    raise Exception("❌ بيانات الدخول غير صحيحة")

def run_money_back(num, token, mode='SCAN'):
    headers = {
        'channel': 'MOBILE', 'useCase': 'Promo', 'Authorization': f'Bearer {token}',
        'api-version': 'v2', 'x-agent-operatingsystem': '11', 'clientId': 'AnaVodafoneAndroid',
        'x-agent-device': 'OPPO CPH2059', 'x-agent-version': '2024.3.3', 'x-agent-build': '593',
        'msisdn': num, 'Content-Type': 'application/json', 'Accept': 'application/json',
        'Accept-Language': 'ar', 'User-Agent': 'okhttp/4.11.0'
    }
    if mode == 'SCAN':
        url = f'https://web.vodafone.com.eg/services/dxl/usage/usageConsumptionReport?bucket.product.publicIdentifier={num}&@type=aggregated'
        res = requests.get(url, headers=headers, timeout=30)
        if res.status_code == 200:
            return extract_money_amount(res.json())
        return 0
    return 0

def extract_money_amount(flex_data):
    try:
        for item in flex_data:
            if item.get('@type') == 'OTHERS' or item.get('usageType') == 'money':
                for bucket in item.get('bucket', []):
                    if bucket.get('usageType') == 'money':
                        for balance in bucket.get('bucketBalance', []):
                            if balance.get('@type') == 'Remaining':
                                return balance.get('remainingValue', {}).get('amount', 0)
        return 0
    except: return 0

def execute_order(num, token, target_id, flow_type):
    url = "https://mobile.vodafone.com.eg/services/dxl/pom/productOrder"
    headers = {'Authorization': f'Bearer {token}', 'msisdn': num, 'Content-Type': 'application/json', 'User-Agent': 'okhttp/4.11.0'}
    if flow_type == "REFUND":
        payload = {"orderItem": [{"action": "add", "product": {"characteristic": [{"name": "WorkflowName", "value": "SelfRefund"},{"name": "EncProductID", "value": target_id}],"relatedParty": [{"id": num, "role": "Subscriber"}]}}], "@type": "MoneyBack"}
    else:
        payload = {"orderItem": [{"action": "add", "product": {"characteristic": [{"name": "TariffID", "value": target_id}],"relatedParty": [{"id": num, "role": "Subscriber"}]}}], "@type": "InterventionTariff"}
    res = requests.post(url, json=payload, headers=headers, timeout=30)
    return res.status_code in [200, 201]

def family_op(owner_num, token, member_num, op_type, quota="10", m_token=None):
    url = "https://web.vodafone.com.eg/services/dxl/cg/customerGroupAPI/customerGroup"
    t = token if op_type != 'ACCEPT' else m_token
    m = owner_num if op_type != 'ACCEPT' else member_num
    h = {'Authorization': f"Bearer {t}", 'msisdn': m, 'Content-Type': "application/json", 'User-Agent': 'okhttp/4.11.0', 'clientId': 'AnaVodafoneAndroid'}
    
    if op_type == 'SEND':
        payload = {"name": "FlexFamily", "type": "SendInvitation", "category": [{"value": "523", "listHierarchyId": "PackageID"},{"value": "47", "listHierarchyId": "TemplateID"},{"value": "523", "listHierarchyId": "TierID"},{"value": "percentage", "listHierarchyId": "familybehavior"}], "parts": {"member": [{"id": [{"value": owner_num, "schemeName": "MSISDN"}], "type": "Owner"},{"id": [{"value": member_num, "schemeName": "MSISDN"}], "type": "Member"}],"characteristicsValue": {"characteristicsValue": [{"characteristicName": "quotaDist1", "value": quota, "type": "percentage"}]}}}
        res = requests.post(url, json=payload, headers=h)
        return res.status_code in [200, 201]
    elif op_type == 'ACCEPT':
        payload = {"category": [{"listHierarchyId": "TemplateID", "value": "47"}],"name": "FlexFamily","parts": {"member": [{"id": [{"schemeName": "MSISDN", "value": f"2{owner_num}"}], "type": "Owner"},{"id": [{"schemeName": "MSISDN", "value": f"2{member_num}"}], "type": "Member"}]},"type": "AcceptInvitation"}
        res = requests.patch(url, json=payload, headers=h)
        return res.status_code in [200, 204]
    elif op_type == 'REMOVE':
        payload = {"name": "FlexFamily", "type": "RemoveMember", "parts": {"member": [{"id": [{"value": owner_num, "schemeName": "MSISDN"}], "type": "Owner"},{"id": [{"value": member_num, "schemeName": "MSISDN"}], "type": "Member"}]}}
        res = requests.patch(url, json=payload, headers=h)
        return res.status_code in [200, 204]
    return False

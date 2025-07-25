import re

def extract_curl_headers(curl_command: str) -> dict:
    """curl 'https://music.youtube.com/youtubei/v1/browse?ctoken=4qmFsgKlAhIMRkVtdXNpY19ob21lGpQCQ0FONnlnRkhTVTlZZGsxNWRqRlpORVJYYjAxQ1EyOUJRa05wVWpWa1JqbDNXVmRrYkZnelRuVlpXRUo2WVVjNU1GZ3lNVEZqTW14cVdETkNhRm95Vm1aamJWWnVZVmM1ZFZsWGQxTklNVVY1VFZoS1lVeFVaRVpoYTBweVdURldSRTlIVFRCTVdFWnlXa2RzVGxkV09VbFdSVTV1WlVkellVNHdNVEZqTW14cVVrZHNlbGt5T1RKYVdFbzFWVWRHYmxwV1RteGpibHB3V1RKVmRGSXlWakJUUnpsMFdsWkNhRm95VlVGQlVVSndaSGRCUWxOVmQwRkJWV3hOUVVGRlFrRjNSRFp1VFdVNVExRkpTVUpC&continuation=4qmFsgKlAhIMRkVtdXNpY19ob21lGpQCQ0FONnlnRkhTVTlZZGsxNWRqRlpORVJYYjAxQ1EyOUJRa05wVWpWa1JqbDNXVmRrYkZnelRuVlpXRUo2WVVjNU1GZ3lNVEZqTW14cVdETkNhRm95Vm1aamJWWnVZVmM1ZFZsWGQxTklNVVY1VFZoS1lVeFVaRVpoYTBweVdURldSRTlIVFRCTVdFWnlXa2RzVGxkV09VbFdSVTV1WlVkellVNHdNVEZqTW14cVVrZHNlbGt5T1RKYVdFbzFWVWRHYmxwV1RteGpibHB3V1RKVmRGSXlWakJUUnpsMFdsWkNhRm95VlVGQlVVSndaSGRCUWxOVmQwRkJWV3hOUVVGRlFrRjNSRFp1VFdVNVExRkpTVUpC&type=next&itct=CBAQybcCIhMIwoSQzK_VjgMV-M9JBx0ebhIx&prettyPrint=false' \
  -H 'accept: */*' \
  -H 'accept-language: en-GB,en;q=0.5' \
  -H 'authorization: SAPISIDHASH 1753355867_1eb44c54eb6c57f223a264fa2ac4878b44d1202f_u SAPISID1PHASH 1753355867_1eb44c54eb6c57f223a264fa2ac4878b44d1202f_u SAPISID3PHASH 1753355867_1eb44c54eb6c57f223a264fa2ac4878b44d1202f_u' \
  -H 'content-type: application/json' \
  -b 'VISITOR_INFO1_LIVE=mOK24p9FE5w; VISITOR_PRIVACY_METADATA=CgJJTBIEGgAgGw%3D%3D; LOGIN_INFO=AFmmF2swRgIhAOCCYNhdWbEHPFdzaqXeLq5qKZgFS3OPv2xUgGmbJdNaAiEA52hI-GBigI2L59G2vvh4vZsHJwpQXs8RKocAGtRhYuE:QUQ3MjNmeDBUeWNZVHhDT3FFTTVsaWhnWXgyOFc5dE5aTmtyaHpjLXhYcEJsNm5FX3VERkZDSWZHQlJYaUNwYmM4WkxPNUV4Tms4TTJWRUhNNVNPenc4LUEzdERTLUQ3czRZYm1YZ3RlV1gyRk9CS3BhNTMzemUzbmR3SWphdWNQXzZwV0IyMGN0Ylh3N2IybWFEZU54UVF6cDBoTDZaR0FB; PREF=f6=40000000&tz=Asia.Jerusalem&f7=100&f5=30000&f4=4000000; __Secure-1PSIDTS=sidts-CjEB5H03PwvsYNXM6wMYJfN841mEkmNTVphc_Q9vCK5uUyHaMZrkyktho4pGfM3P_4bBEAA; __Secure-3PSIDTS=sidts-CjEB5H03PwvsYNXM6wMYJfN841mEkmNTVphc_Q9vCK5uUyHaMZrkyktho4pGfM3P_4bBEAA; HSID=AdM5Y4UJLJg4fNUj2; SSID=A6X0XB0Lz1ZqAkzUr; APISID=u20JrfFRtIgRgasj/Ac0FnDu3dIcLvoeTk; SAPISID=o-drsQnJl30tHg8k/A5EE3IXlJ9g1XPu-T; __Secure-1PAPISID=o-drsQnJl30tHg8k/A5EE3IXlJ9g1XPu-T; __Secure-3PAPISID=o-drsQnJl30tHg8k/A5EE3IXlJ9g1XPu-T; SID=g.a000zgjV3McJRmq0mVzxJB0XlXaAp6ymJuT68HjSrp_fRWoGvJdJx268zFoSpb534prsaHcmwQACgYKAXASARESFQHGX2Mi58UeuvvorYcpMsI1oLmqFhoVAUF8yKr6taprN7plT4l58ltpD6lB0076; __Secure-1PSID=g.a000zgjV3McJRmq0mVzxJB0XlXaAp6ymJuT68HjSrp_fRWoGvJdJc146C7pbynQazLc8cISa2AACgYKAQASARESFQHGX2MinVYH_Q5CkRKO_aS7FuHWaBoVAUF8yKrCRFifWxYP15eucJ7Dtf_-0076; __Secure-3PSID=g.a000zgjV3McJRmq0mVzxJB0XlXaAp6ymJuT68HjSrp_fRWoGvJdJ3fTW4AVEDMo_xCMwOO7_OAACgYKAW4SARESFQHGX2MiaPTQnO_G5RjLH03U9v2FOBoVAUF8yKrL_NnocJA_IO0nAdrhVVKG0076; YSC=QubzDSFmD0M; __Secure-ROLLOUT_TOKEN=CJnMzZvN3P2IwgEQ6fKx4MT_jQMY-430hojVjgM%3D; SIDCC=AKEyXzXBHGgQI-5EzrqCoHhnkTQbQ1gejxPCVWWwQ9MJ17V0iWvPUxPhlqVMzD9sEmLUlmne; __Secure-1PSIDCC=AKEyXzWiASnXnbULQZfUhW_H95mf_79FGqJntY4rJsUkZQI-esBPCeJr8QD2NgfwETZRRSgPMg; __Secure-3PSIDCC=AKEyXzWVmzlaDqiScus2k0kbuGF6agAFulJkhmaM6qaCjLMe8L2NI74mdB4cRCwBFefEfcsIWw' \
  -H 'origin: https://music.youtube.com' \
  -H 'priority: u=1, i' \
  -H 'referer: https://music.youtube.com/' \
  -H 'sec-ch-ua: "Not)A;Brand";v="8", "Chromium";v="138", "Brave";v="138"' \
  -H 'sec-ch-ua-arch: "x86"' \
  -H 'sec-ch-ua-bitness: "64"' \
  -H 'sec-ch-ua-full-version-list: "Not)A;Brand";v="8.0.0.0", "Chromium";v="138.0.0.0", "Brave";v="138.0.0.0"' \
  -H 'sec-ch-ua-mobile: ?0' \
  -H 'sec-ch-ua-model: ""' \
  -H 'sec-ch-ua-platform: "Windows"' \
  -H 'sec-ch-ua-platform-version: "19.0.0"' \
  -H 'sec-ch-ua-wow64: ?0' \
  -H 'sec-fetch-dest: empty' \
  -H 'sec-fetch-mode: same-origin' \
  -H 'sec-fetch-site: same-origin' \
  -H 'sec-gpc: 1' \
  -H 'user-agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36' \
  -H 'x-goog-authuser: 0' \
  -H 'x-goog-visitor-id: CgttT0syNHA5RkU1dyjZrIjEBjIKCgJJTBIEGgAgGw%3D%3D' \
  -H 'x-origin: https://music.youtube.com' \
  -H 'x-youtube-bootstrap-logged-in: true' \
  -H 'x-youtube-client-name: 67' \
  -H 'x-youtube-client-version: 1.20250716.03.00' \
  --data-raw '{"context":{"client":{"hl":"iw","gl":"IL","remoteHost":"46.117.251.29","deviceMake":"","deviceModel":"","visitorData":"CgttT0syNHA5RkU1dyjZrIjEBjIKCgJJTBIEGgAgGw%3D%3D","userAgent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36,gzip(gfe)","clientName":"WEB_REMIX","clientVersion":"1.20250716.03.00","osName":"Windows","osVersion":"10.0","originalUrl":"https://music.youtube.com/","screenPixelDensity":1,"platform":"DESKTOP","clientFormFactor":"UNKNOWN_FORM_FACTOR","configInfo":{"appInstallData":"CNmsiMQGEJHRzxwQiOOvBRCYuc8cEOK-zxwQ_LLOHBDGjs8cEJe1zxwQ6rvPHBC52c4cEK6P_xIQ9cTPHBCBzc4cEJOGzxwQyfevBRC45M4cEImwzhwQ4svPHBDwnc8cENr3zhwQzqzPHBDMwM8cEIGzzhwQlP6wBRC-irAFEJ7QsAUQmY2xBRDFw88cENPhrwUQt-r-EhDhys8cEPXLzxwQkLzPHBDiuLAFEMfIzxwQpcvPHBCfoc8cEPa6zxwQ3rzOHBDYnM8cEIeszhwQu9nOHBDw4s4cEPLEzxwQzN-uBRDwxM8cEParsAUQvZmwBRDGy88cEImXgBMQvbauBRCKgoATEJmYsQUQiIewBRCwhs8cEM61zxwqJENBTVNGUlVXb0wyd0ROSGtCdUhkaFFyTDNBNnZpQVlkQnc9PQ%3D%3D","coldConfigData":null,"coldHashData":null,"hotHashData":null},"screenDensityFloat":1,"userInterfaceTheme":"USER_INTERFACE_THEME_DARK","timeZone":"Asia/Jerusalem","browserName":"Chrome","browserVersion":"138.0.0.0","acceptHeader":"text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8","deviceExperimentId":"ChxOelV6TURZd05qQTVPRGd5TXpjNU9EazRPQT09ENmsiMQGGNmsiMQG","rolloutToken":"CJnMzZvN3P2IwgEQ6fKx4MT_jQMY-430hojVjgM%3D","screenWidthPoints":862,"screenHeightPoints":1310,"utcOffsetMinutes":180,"musicAppInfo":{"pwaInstallabilityStatus":"PWA_INSTALLABILITY_STATUS_UNKNOWN","webDisplayMode":"WEB_DISPLAY_MODE_BROWSER","storeDigitalGoodsApiSupportStatus":{"playStoreDigitalGoodsApiSupportStatus":"DIGITAL_GOODS_API_SUPPORT_STATUS_UNSUPPORTED"}}},"user":{"lockedSafetyMode":false},"request":{"useSsl":true,"internalExperimentFlags":[],"consistencyTokenJars":[]},"adSignalsInfo":{"params":[{"key":"dt","value":"1753355865399"},{"key":"flash","value":"0"},{"key":"frm","value":"0"},{"key":"u_tz","value":"180"},{"key":"u_his","value":"3"},{"key":"u_h","value":"1440"},{"key":"u_w","value":"2560"},{"key":"u_ah","value":"1440"},{"key":"u_aw","value":"2560"},{"key":"u_cd","value":"24"},{"key":"bc","value":"31"},{"key":"bih","value":"1310"},{"key":"biw","value":"847"},{"key":"brdim","value":"2,4,2,4,2560,0,865,1317,862,1310"},{"key":"vis","value":"1"},{"key":"wgl","value":"true"},{"key":"ca_type","value":"image"}]}}}'"""
    headers = {}
    # Regex to find -H 'header-name: header-value'
    # It handles cases where values might contain escaped quotes or various characters.
    # It also handles leading/trailing whitespace around the header name/value parts.
    header_pattern = re.compile(r"-H\s+'([^:]+):\s*([^']+)'")

    # Find all matches in the cURL command
    matches = header_pattern.finditer(curl_command)

    for match in matches:
        header_name = match.group(1).strip()
        header_value = match.group(2).strip()
        headers[header_name] = header_value
    return headers

# Your example cURL command (it's long, so good for testing)
curl_command = """
curl 'https://music.youtube.com/browse' \
  -H 'authority: music.youtube.com' \
  -H 'accept: */*' \
  -H 'accept-language: en-US,en;q=0.9,he;q=0.8' \
  -H 'content-type: application/json' \
  -H 'cookie: __Secure-3PAPISID=...; __Secure-3PSID=...; ...' \
  -H 'origin: https://music.youtube.com' \
  -H 'referer: https://music.youtube.com/' \
  -H 'user-agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36' \
  -H 'x-goog-authuser: 0' \
  -H 'x-origin: https://music.youtube.com' \
  --data-raw '{"context":{"client":{"clientName":"WEB_REMIX","clientVersion":"1.20240321.01.00","gl":"US","hl":"en"},"user":{"lockedSafetyMode":false}},"browseId":"FEmusic_home"}' \
  --compressed
"""

extracted_headers = extract_curl_headers(curl_command)

# Print the extracted headers for verification
import json
print(json.dumps(extracted_headers, indent=4))
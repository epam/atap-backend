from selenium import webdriver
from json import dumps

from browsermobproxy import Server
from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait

from selenium.common.exceptions import WebDriverException, UnexpectedAlertPresentException

from framework import await_page_load

moved_permanently = 301
see_other = 303
temporary_redirect = 307
permanent_redirect = 308
unauthorized = 401
forbidden = 403
proxy_authentication_required = 407
network_authentication_required = 511

nasty_auth_codes = [unauthorized, forbidden, proxy_authentication_required, network_authentication_required]
redirection_status_codes = [moved_permanently, see_other, temporary_redirect, permanent_redirect]


def network_configured_server_and_driver():
    server = Server("web_interface/backend/browsermob-proxy-2.1.4/bin/browsermob-proxy", {"port": 8020})
    server.start()

    proxy = server.create_proxy(params={"trustAllServers": "true", "port": 8021})

    options = webdriver.FirefoxOptions()
    options.profile = webdriver.FirefoxProfile()

    # * browser security settings, not sure it can't be omitted
    options.profile.set_preference("browser.safebrowsing.blockedURIs.enabled", False)
    options.profile.set_preference("browser.safebrowsing.downloads.enabled", False)
    options.profile.set_preference("browser.safebrowsing.downloads.remote.block_dangerous", False)
    options.profile.set_preference("browser.safebrowsing.downloads.remote.block_dangerous_host", False)
    options.profile.set_preference("browser.safebrowsing.downloads.remote.block_potentially_unwanted", False)
    options.profile.set_preference("browser.safebrowsing.downloads.remote.block_uncommon", False)
    options.profile.set_preference("browser.safebrowsing.downloads.remote.enabled", False)
    options.profile.set_preference("browser.safebrowsing.malware.enabled", False)
    options.profile.set_preference("browser.safebrowsing.phishing.enabled", False)

    options.profile.set_preference("network.proxy.type", 1)
    options.profile.set_preference("network.proxy.http", "localhost")
    options.profile.set_preference("network.proxy.http_port", proxy.port)
    options.profile.set_preference("network.proxy.ssl", "localhost")
    options.profile.set_preference("network.proxy.ssl_port", proxy.port)
    options.profile.set_preference("network.proxy.ftp", "localhost")
    options.profile.set_preference("network.proxy.ftp_port", proxy.port)
    options.profile.set_preference("network.proxy.share_proxy_settings", True)

    capabilities = DesiredCapabilities.FIREFOX
    capabilities["acceptSslCerts"] = True

    proxy.add_to_capabilities(capabilities)

    driver = webdriver.Firefox(options=options, desired_capabilities=capabilities)

    return proxy, server, driver


def login_successful(response, driver, redirected, login_request, redirect_get_response):
    if not response:
        return False

    if redirected and redirect_get_response is None:
        return "Fast Delay Interim"

    response_type = response["content"]["mimeType"]
    json_response_type = response_type == "application/json"
    html_response_type = response_type.find("text/html") != -1

    has_error_msg = False
    if json_response_type:
        has_error_msg = json_response_type and "error" in str(response["content"])
    elif html_response_type:  # * expect 200 status
        active_login_fields_selector = ", ".join(
            [f'input[type="{_type}"][value="{auth_proceed.login}"]' for _type in ["tel", "email", "text"]]
        )
        active_password_fields = driver.execute_script(
            """
                return [...document.querySelectorAll(arguments[0])].filter(
                f => f.value === arguments[1] || document.activeElement === f
                );
            """,
            "input[type='password']",
            auth_proceed.password,
        )

        has_error_msg = bool(driver.find_elements_by_css_selector(active_login_fields_selector)) or bool(
            active_password_fields
        )

    return response["status"] not in nasty_auth_codes and not has_error_msg


def response_is_ready(response):
    return response is None or response.get("_error") is None  # * "No response received"


def verify_login_request(driver, proxy, do_auth, need_btn):
    har_filename = f'{auth_proceed.url.split(".")[-2]}_lag_{auth_proceed.delay}'

    login_page_url = driver.current_url  # * may differ from url for modal auth

    proxy.new_har(
        har_filename,
        options={"captureHeaders": True, "captureContent": True, "captureBinaryContent": False},
    )

    safe_output = do_auth(
        driver,
        dumps(auth_proceed.auth_options),
        modal=need_btn,
        url=auth_proceed.url,
    )
    await_page_load.wait_for_page_load(driver)

    if safe_output is not None:  # * direct auth activated
        return safe_output

    proxy.wait_for_traffic_to_stop(1, auth_proceed.delay)

    har = proxy.har

    login_response = None
    need_get, location, auth_get_response = False, "", None

    for ent in har["log"]["entries"]:
        request = ent["request"]
        response = ent["response"]
        main_url = request["url"].find(login_page_url[login_page_url.find("//") + 1 :].split("/")[1])

        if need_get:
            if request["method"] == "GET":
                if request["url"] == location:
                    auth_get_response = response
                if auth_get_response and 200 <= response["status"] < 300:
                    auth_get_response = response
                    break
            continue

        if request["method"] == "POST" and main_url != -1 and request.get("postData") is not None:
            if not auth_proceed.password:
                auth_proceed.password = auth_proceed.login or "password"  # * handle empty credentials

            if not login_response and auth_proceed.password in str(request["postData"]):
                login_response = response  # * first caught response, clicking returns error response after OK

                if response["status"] in redirection_status_codes:
                    location = [header for header in response["headers"] if header["name"] == "Location"]
                    location = location and location[0]["value"] or ""
                    need_get = bool(location)

    else:
        auth_get_response = None

    if locals().get("request"):  # * may collect 0 requests
        login_response = auth_get_response or login_response

        if not response_is_ready(login_response):
            return "Fast Delay Interim"

        return login_successful(login_response, driver, need_get, request, auth_get_response)

    return False


def auth_proceed(auth_function):
    def wrapper(framework_driver, auth_options, url, listening_lag_ms, modal):
        if auth_function.__name__.endswith("page"):
            url = auth_options["activator"]

        auth_proceed.url, auth_proceed.delay = url, listening_lag_ms
        auth_proceed.login, auth_proceed.password = auth_options["login"], auth_options["password"]
        auth_proceed.auth_options = auth_options

        try:
            proxy, proxy_server, driver = network_configured_server_and_driver()

            driver.get(url)

            return verify_login_request(driver, proxy, auth_function, need_btn=modal)
        finally:
            proxy_server.stop()
            driver.quit()

    return wrapper

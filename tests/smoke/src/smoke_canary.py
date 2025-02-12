import os

from aws_synthetics.selenium import synthetics_webdriver as syn_webdriver
from aws_synthetics.common import synthetics_logger as logger

screenshot_dir = os.environ.get("SCREENSHOT_DIR", "/tmp/screenshots")


def main():
    base_url = os.environ.get("BASE_URL")
    browser = syn_webdriver.Chrome()

    paths = ["/digital-land/issue_type", "/digital-land/issue"]
    for path in paths:
        visit_and_screenshot(browser, base_url, path)

    logger.info("Canary successfully executed.")


def visit_and_screenshot(browser, base_url, path):
    url = base_url + path
    browser.get(url)
    browser.save_screenshot(f"${screenshot_dir}/${path}.png")
    response = syn_webdriver.get_http_response(url)
    if response == 'error':
        raise Exception("Failed to load page!")


def handler(event, context):
    return main()

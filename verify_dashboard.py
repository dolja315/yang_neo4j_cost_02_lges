from playwright.sync_api import sync_playwright, expect
import os
import time

def verify_dashboard(page):
    # Navigate to the dashboard
    page.goto("http://localhost:8000/")

    # Wait for the page to load
    page.wait_for_selector("body")

    # Click on "Process Monitoring" tab (Tab 2)
    # The button has id="btn-tab-2" and text "Process Monitoring"
    page.click("#btn-tab-2")

    # Wait for tab content to be active
    expect(page.locator("#tab-2")).to_have_class("tab-content active")

    # Check for Bottom Analysis Panel
    # It should exist but be hidden
    panel = page.locator("#bottom-analysis-panel")
    expect(panel).to_be_attached()
    expect(panel).to_have_class(lambda c: "hidden" in c)

    # Check that Drawer is GONE (or at least not visible/open, but I removed it from DOM)
    # The selector #drawer should NOT exist
    drawer = page.locator("#drawer")
    expect(drawer).not_to_be_attached()

    # Check Heatmap container
    # Since Neo4j is down, it should show "No process data available"
    # Wait a bit for the fetch to fail/return empty
    time.sleep(2)
    heatmap_container = page.locator("#process-flow")
    expect(heatmap_container).to_contain_text("No process data available")

    # Take screenshot
    page.screenshot(path="dashboard_verification.png")
    print("Verification successful!")

if __name__ == "__main__":
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            verify_dashboard(page)
        except Exception as e:
            print(f"Verification failed: {e}")
            page.screenshot(path="verification_failure.png")
        finally:
            browser.close()

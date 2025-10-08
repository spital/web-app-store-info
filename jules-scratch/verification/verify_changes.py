from playwright.sync_api import sync_playwright, expect

def run_verification():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        try:
            # Navigate to the login page
            page.goto("http://localhost:8888/login")

            # Fill in the login form
            page.get_by_placeholder("Uživatelské jméno").fill("testuser")
            page.get_by_placeholder("Heslo").fill("testpassword")
            page.get_by_role("button", name="Přihlásit").click()

            # Wait for navigation and verify the dashboard
            expect(page).to_have_url("http://localhost:8888/")
            expect(page.get_by_text("Vítejte, testuser!")).to_be_visible()

            # Verify the new note form is present
            expect(page.get_by_placeholder("Napište rychlou poznámku a uložte ji...")).to_be_visible()

            # Take a screenshot of the dashboard
            page.screenshot(path="jules-scratch/verification/verification.png")

            print("Verification script completed successfully and screenshot taken.")

        except Exception as e:
            print(f"An error occurred during verification: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    run_verification()
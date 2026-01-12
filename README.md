# 📘 Project Documentation: DemoBlaze E2E Automation

## 1. Project Description

This project is a robust **End-to-End (E2E) Automation Framework** designed to validate the critical purchasing workflows on the [DemoBlaze](https://www.demoblaze.com/) e-commerce platform.

Built using **Playwright** with **TypeScript**, the framework adheres to the **Page Object Model (POM)** design pattern. This ensures that the test logic is strictly separated from the UI interaction logic, resulting in a codebase that is clean, maintainable, and scalable.

**Key Technical Features:**

* **Smart Waits:** Utilizes API response interception (`waitForResponse`) and visual state validation (`waitFor`) to eliminate flaky tests caused by network latency, avoiding unreliable "hard waits."
* **Facade Pattern:** Implements a central `PageManager` to streamline page initialization.
* **Data Driven:** dynamically generates unique user credentials for every test run to ensure data isolation.
* **Encapsulation:** Protects internal page logic (e.g., accessing the `page` fixture) to prevent brittle tests.

---

## 2. User Story

**Title:** Purchase Flow & Price Audit for Laptops

**As a** registered customer on the DemoBlaze e-commerce website,
**I want to** browse the catalog, filter for laptops, and add specific items to my cart,
**So that** I can review my order with the correct total price and complete the purchase successfully.

### ✅ Acceptance Criteria (AC)

1. **Registration & Authentication:**
* The user must be able to create a new account with a unique username.
* The user must be able to log in immediately with those credentials.


2. **Product Discovery & Selection:**
* The user must navigate to the "Laptops" category.
* The user must select and add the following specific products to the cart:
* *MacBook Pro*
* *Sony vaio i5*




3. **Data Integrity (Price Audit):**
* The system must capture the price of each item from the Product Details page before adding it to the cart.
* The total price displayed in the Cart must exactly match the sum of the individual product prices.


4. **Checkout Process:**
* The user must be able to initiate the "Place Order" flow from the cart.
* The user must be able to fill out the shipping and payment information form.


5. **Completion:**
* Upon submission, a confirmation modal must appear containing the text "Thank you for your purchase!".



---

## 3. Project Structure & Architecture

The project follows a modular directory structure designed for scalability.

```text
project-root/
│
├── 📂 fixtures/
│   └── baseTest.ts
│   📝 Purpose: Extends the standard Playwright test runner. It automatically 
│      injects the "PageManager" instance into every test, removing the need 
│      for manual setup in spec files.
│
├── 📂 pages/
│   ├── 📂 base/
│   │   ├── BasePage.ts
│   │   📝 Purpose: The parent class. Contains shared methods used by all pages, 
│   │      such as handling browser alerts and generic navigation.
│   │   └── PageManager.ts
│   │   📝 Purpose: The "Traffic Controller." It initializes all Page Objects 
│   │      (Home, Login, Cart, etc.) and exposes them via a single object (`pm`).
│   │
│   ├── 📂 auth/
│   │   ├── LoginPage.ts      # Handles Login modal interactions.
│   │   └── SignUpPage.ts     # Handles Registration modal interactions.
│   │
│   ├── 📂 products/
│   │   ├── HomePage.ts       # Main navigation and category filtering.
│   │   ├── CategoriesPage.ts # Handles selecting products from the grid.
│   │   └── ProductDetailsPage.ts
│   │       📝 Purpose: Captures product prices and handles the "Add to Cart" 
│   │          logic using Smart Waits for API responses.
│   │
│   └── 📂 checkout/
│       ├── CartPage.ts       # Validates table rows and totals.
│       └── CheckoutPage.ts   # Fills the order form and submits.
│
├── 📂 utils/
│   └── TestHelpers.ts
│   📝 Purpose: A utility class for non-UI logic. Specifically used to generate 
│      random/unique usernames and passwords based on timestamps.
│
└── 📂 tests/
    └── e2ePurchase.spec.ts
    📝 Purpose: The executable test file. It contains the business logic 
       (the User Story steps) and assertions, without containing any CSS selectors.

```

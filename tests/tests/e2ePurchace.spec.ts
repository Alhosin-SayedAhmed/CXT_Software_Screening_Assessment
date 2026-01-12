import { test, expect } from '../fixtures/baseTest';
import { TestHelper } from '../utils/TestHelpers';

test.describe('E2E Purchase', () => {

  // Variables
  let expectedsum = 0;
  // Setup : Generate a unique username and password
  const user = TestHelper.generateUser();
  const productsToBuy = ['MacBook air', 'Sony vaio i5'];



  test('Purchase a product', async ({ pm }) => {

    console.log('---  Test Started ---');

    // Scenario 1: Verify that User Can Sign Up Successfully 

    await pm.homePage.navigateTo();
    await pm.homePage.goToSignUp();
    await pm.signUpPage.register(user.username, user.password);

    // Scenario 2: Verify that Two Products Are Purchased Successfully 
    // Step 1: Log In 
    await pm.homePage.goToLogin();
    await pm.loginPage.login(user.username, user.password);

    // Step 2&3 : Purchase the products
    for (const productName of productsToBuy) {
      await pm.homePage.navigateTo();
      await pm.homePage.selectLaptop();

      // navigate To product Details Page
      await pm.categorisPage.selectProduct(productName);

      // Catch the product price
      const price = await pm.productDetailsPage.getPrice();
      expectedsum += price;

      console.log(`Product: ${productName.padEnd(12)} ,Price: $${price}`);

      // Add the product to the cart
      await pm.productDetailsPage.addToCart();
    }

    // Step 4: Verify the cart total price
    await pm.homePage.goToCart();

    // Extract the cart total price & Title
    const cartItems = await pm.cartPage.getCartItems();
    const totalPrice = await pm.cartPage.getTotalPrice();


    
    //Displayed data founded in the cart
    console.log('\n---Cart Table Data ----');
    cartItems.forEach((item, i) => {
      console.log(`${i + 1}. ${item.name.padEnd(15)} : $${item.price}`);
    });
    


    // Step 5: Verify Total Amount Calculation 
    // ASSERTION THE TOTAL PRICE
    console.log(`/n Results -> Expected : $${expectedsum} , Displayed : $${totalPrice}`);
    expect(totalPrice).toBe(expectedsum);
    console.log('Success : The Total Price Matches The Expected Sum');

    // Step 6: Checkout
    await pm.cartPage.placeOrder();
    
    await pm.checkoutPage.fillOrderForm({
      name: 'Alhussein',
      country: 'Egypt',
      city: 'cairo',
      card: '+201272149450',
      month: '2',
      year: '2000',
    });
    
    const successMessage = await pm.checkoutPage.submitOrder();
    //Assertion
    expect(successMessage).toContain('Thank you for your purchase!');
    
    // TODO: Add cart verification and purchase completion logic here

    console.log('---  Test Completed ---');
  });
});
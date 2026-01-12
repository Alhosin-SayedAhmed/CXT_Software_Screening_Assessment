import { Page } from '@playwright/test';
import { HomePage } from '../prpducts/HomePage';
import { SignUpPage } from '../auth/SignUpPage';
import { LoginPage } from '../auth/LoginPage';
import { CategorisPage } from '../prpducts/CategorisPage';
import { ProductDetailsPage } from '../prpducts/ProductDetailsPage';
import { CartPage } from '../checkout/CartPage';
import { CheckoutPage } from '../checkout/CheckoutPage';





export class PageManager {

    /********Variables***** */

    readonly homePage: HomePage;
    readonly signUpPage: SignUpPage;
    readonly loginPage: LoginPage;
    readonly categorisPage: CategorisPage;
    readonly productDetailsPage: ProductDetailsPage;
    readonly cartPage: CartPage;
    readonly checkoutPage: CheckoutPage;



    /******Actions******** */

    constructor(page: Page) {
        // Initialize all page opbject
        this.homePage = new HomePage(page);
        this.signUpPage = new SignUpPage(page);
        this.loginPage = new LoginPage(page);
        this.categorisPage = new CategorisPage(page);
        this.productDetailsPage = new ProductDetailsPage(page);
        this.cartPage = new CartPage(page);
        this.checkoutPage = new CheckoutPage(page);

    }



}
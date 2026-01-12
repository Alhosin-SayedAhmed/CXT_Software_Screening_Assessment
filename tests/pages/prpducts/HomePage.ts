import { BasePage } from '../base/BasePage';




export class HomePage extends BasePage {


    // Actions

    // Methodes to navigate via the top navigatio bar

    async goToSignUp() { await this.page.locator('#signin2').click(); }
    async goToLogin() { await this.page.locator('#login2').click(); }

    async selectLaptop() { await this.page.getByRole('link', { name: 'Laptops' }).click(); }

    async goToCart() { await this.page.getByRole('link', { name: 'Cart', exact: true }).click(); }


}
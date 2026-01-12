import { BasePage } from '../base/BasePage';

export class ProductDetailsPage extends BasePage {

    //Actions

    // Extract the product price as integr
    async getPrice(): Promise<number> {

        // Wait for the price element to be visible
        await this.page.locator('h3.price-container').waitFor();

        // Extract the price text
        const priceText = await this.page.locator('h3.price-container').innerText();

        // Remove the currency symbol and convert to number
        return parseInt(priceText.replace(/[^0-9]/g, ''));

    }

    // Add the product to the cart
    async addToCart() {
        // Prepare to handle the alert
        await this.handleAlert();

        // Add the product to the cart
        const responsePromise = this.page.waitForResponse(response => response.url().includes('addtocart'));

        // Click the add to cart button
        await this.page.getByRole('link', { name: 'Add to cart' }).click();

        // Wait for the response
        await responsePromise;
    }

}
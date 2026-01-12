import { BasePage } from "../base/BasePage";

export class CheckoutPage extends BasePage {

    // Actions

    // Fill the checkout form
    async fillOrderForm(details: any) {

        await this.page.locator('#name').fill(details.name);
        await this.page.locator('#country').fill(details.country);
        await this.page.locator('#city').fill(details.city);
        await this.page.locator('#card').fill(details.card);
        await this.page.locator('#month').fill(details.month);
        await this.page.locator('#year').fill(details.year);

    }

    async submitOrder() {
        await this.page.getByRole('button', { name: 'Purchase' }).click();
        return await this.page.locator('.sweet-alert h2').innerText();
    }

}
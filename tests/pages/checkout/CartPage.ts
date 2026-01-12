import { BasePage } from "../base/BasePage";

export class CartPage extends BasePage {

    // Actions


    async getCartItems(): Promise<{ name: string, price: number }[]> {
        const items: { name: string, price: number }[] = [];

        // wait until the table bodys are visible
        await this.page.locator('#tbodyid').waitFor({ state: 'visible' });

        // IF cart is empty return empty array
        try {
            // Short timeout to check if items exist without waiting too long
            await this.page.locator('#tbodyid tr').first().waitFor({ state: 'visible', timeout: 3000 });
        }
        catch (error) {
            console.log('Cart is empty');
            return items;
        }

        // Extract Text from table
        const rows = await this.page.locator('#tbodyid tr').all();

        for (const row of rows) {
            const name = await row.locator('td:nth-child(2)').innerText();
            const price = await row.locator('td:nth-child(3)').innerText();
            items.push({ name: name.trim(), price: parseInt(price) });
        }

        return items;
    }


    // Get the total price of the cart
    async getTotalPrice(): Promise<number> {
        await this.page.locator('#totalp').waitFor({ state: 'visible' });
        const rawText = await this.page.locator('#totalp').innerText();
        return parseInt(rawText.replace(/[^0-9]/g, ''));
    }

    // click on checkout button
    async placeOrder() {
        await this.page.getByRole('button', { name: 'Place Order' }).click();
    }
}
import { BasePage } from "../base/BasePage";

export class CategorisPage extends BasePage {

    // Actions

    // Select a specific product
    async selectProduct(name: string) {
        await this.page.getByRole('link', { name }).click();
    }

}

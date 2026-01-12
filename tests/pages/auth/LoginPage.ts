import { BasePage } from '../base/BasePage';


export class LoginPage extends BasePage {

    // Actions

    async login(username: string, password: string) {

        // Fill the login form
        await this.page.locator('#loginusername').fill(username);
        await this.page.locator('#loginpassword').fill(password);

        // Submit the form
        await this.page.getByRole('button', { name: 'Log in' }).click();

    }

}

import { BasePage } from "../base/BasePage";


export class SignUpPage extends BasePage {

    // Actions

    async register(username: string, password: string) {

        // Fill the registration form
        await this.page.locator('#sign-username').fill(username);
        await this.page.locator('#sign-password').fill(password);

        // Submit the form
        await this.page.getByRole('button', { name: 'Sign up' }).click();


        //Accept the alert
        await this.handleAlert();


    }

}

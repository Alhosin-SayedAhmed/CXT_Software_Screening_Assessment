import { Page } from "@playwright/test";



export class BasePage {

    /****Variables***** */

    protected page: Page;


    /***Actions ***** */

    constructor(page: Page) {
        this.page = page;
    }


    // Navigate to a specific url path

    async navigateTo(path: string = '/') {
        await this.page.goto(path);
    }


    // Handle the Alerts
    async handleAlert(){
        this.page.once('dialog',async dialog=>{
            console.log(` [Alert]:${dialog.message()}`);
            await dialog.accept();
        })
        
    }
}


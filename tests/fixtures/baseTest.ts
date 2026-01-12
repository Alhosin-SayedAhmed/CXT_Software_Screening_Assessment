import { test as base } from "@playwright/test";
import { PageManager } from "../pages/base/BaseManager";


export const test = base.extend<{ pm: PageManager }>({
    //Actions

    pm: async ({ page }, use) => {
        const pm = new PageManager(page);
        await use(pm);
    }

});

export { expect } from "@playwright/test";
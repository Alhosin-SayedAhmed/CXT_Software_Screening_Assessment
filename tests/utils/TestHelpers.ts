export class TestHelper {

/*** Actions**** */


// Generate A unique Username and Password
static generateUser(){

    const timestamp = Date.now();
    const username = `Alhussaein_${timestamp}`;
    const password = `pass_${timestamp}`;

    return {username, password};

}

}
Feature: Spread income or expense postings over a period

    Scenario: Spread income from paycheque over pay period

        Given the following beancount transaction:
            ;
            2016-06-15 * "The Company" "Salary for June"
                Income:TheCompany:NetSalary     -300.00 EUR
                    spread: "Month @ 2016-06-01"
                Assets:MyBank:Checking           300.00 EUR

        When the beancount-spread plugin is executed

        Then the original transaction should be modified:
            ;
            ; Post the paycheque to a Liabilities:Current:... (a "placeholder" account) instead of Income:...

            2016-06-15 * "The Company" "Salary for June"
                Liabilities:Current:TheCompany:NetSalary       -300.00 EUR
                Assets:MyBank:Checking                          300.00 EUR

        And the following transactions should be generated (not exhaustive):
            ;
            ; Each new transaction transfers a fraction of the balance in the
            ; Liabilities:Current:... account back to Income:...

            2016-06-01 * "The Company" "Salary for June (spread 1/30)" #spreaded
                Liabilities:Current:TheCompany:NetSalary         10.0 EUR
                Income:TheCompany:NetSalary                     -10.0 EUR

            2016-06-02 * "The Company" "Salary for June (spread 2/30)" #spreaded
                Liabilities:Current:TheCompany:NetSalary         10.0 EUR
                Income:TheCompany:NetSalary                     -10.0 EUR
        
            2016-06-03 * "The Company" "Salary for June (spread 3/30)" #spreaded
                Liabilities:Current:TheCompany:NetSalary         10.0 EUR
                Income:TheCompany:NetSalary                     -10.0 EUR
            ;        .
            ;        .
            ;        .

            2016-06-30 * "The Company" "Salary for June (spread 30/30)" #spreaded
                Liabilities:Current:TheCompany:NetSalary         10.0 EUR
                Income:TheCompany:NetSalary                     -10.0 EUR
        

    Scenario: Spread utility bill expenses over billing period

        Given the following beancount transaction:
            ;
            2016-06-15 * "The Company" "Internet bill for June"
                Expenses:Bills:Internet                        -75.00 EUR
                    spreadAfter: "Month @ 2016-06-15"
                Assets:MyBank:Checking                          75.00 EUR

        When the beancount-spread plugin is executed

        Then the original transaction should be modified:
            ;
            ; Post the bill to Assets:Current:... (a "placeholder" account) instead of Expenses:...
            ;

            2016-06-15 * "The Company" "Internet bill for June"
                Assets:Current:Bills:Internet                  -75.00 EUR
                Assets:MyBank:Checking                          75.00 EUR

        And the following transactions should be generated (not exhaustive):
            ;
            ; Each new transaction transfers a fraction of the balance in the
            ; Assets:Current:... account back to Expenses:...
            ;

            2016-06-15 * "The Company" "Internet bill for June (spread 1/30)" #spreaded
                Assets:Current:Bills:Internet                    2.5 EUR
                Expenses:Bills:Internet                         -2.5 EUR

            2016-06-16 * "The Company" "Internet bill for June (spread 2/30)" #spreaded
                Assets:Current:Bills:Internet                    2.5 EUR
                Expenses:Bills:Internet                         -2.5 EUR
        
            2016-06-17 * "The Company" "Internet bill for June (spread 3/30)" #spreaded
                Assets:Current:Bills:Internet                    2.5 EUR
                Expenses:Bills:Internet                         -2.5 EUR
            .
            .
            .

            2016-07-14 * "The Company" "Internet bill for June (spread 30/30)" #spreaded
                Assets:Current:Bills:Internet                    2.5 EUR
                Expenses:Bills:Internet                         -2.5 EUR
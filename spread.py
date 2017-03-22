__author__ = 'Akuukis <akuukis@kalvis.lv'

import datetime
import re
import math

from beancount.core.amount import Amount, add, sub, mul, div
from beancount.core import data
from beancount.core.position import Position
from beancount.core.number import ZERO, D, round_to

from .check_aliases import check_aliases_entry
from .check_aliases import check_aliases_posting
from .get_dates import get_dates
from .parse_params import parse_params

__plugins__ = ['spread']

def get_postings(duration, closing_dates, account, posting, entry, MIN_VALUE):
    new_transactions = []

    ## Distribute value over points. TODO: add new methods
    if(posting.units.number > 0):
        amountEach = math.floor(posting.units.number / duration * 100) / D(str(100))
    else:
        amountEach = math.ceil(posting.units.number / duration * 100) / D(str(100))
    if(abs(amountEach) < abs(MIN_VALUE)):
        if(posting.units.number > 0):
            amountEach = MIN_VALUE
        else:
            amountEach = -MIN_VALUE
        duration = math.floor( abs(posting.units.number) / MIN_VALUE )
        closing_dates = closing_dates[0:duration]
    remainder = sub(posting.units, Amount( amountEach * duration, posting.units.currency) )

    ## Debug
    # print('      Extend %s over %s points %s per each (%s remainder).'%(posting.units, countTransactions, amountEach, remainder))

    ## Double-check leg direction
    if(posting.units.number > 0):
        assert(remainder > Amount(D(str(-0.01)), posting.units.currency))
    else:
        assert(remainder < Amount(D(str(+0.01)), posting.units.currency))

    ## Generate new transactions
    for i, _ in enumerate(closing_dates):
        ## Debug
        # print(amountEach, closing_dates[i], i)

        ## Add remainder to first day.
        if(i == 0):
            amount = add(Amount(D(amountEach), posting.units.currency), remainder)
        else:
            amount = Amount(D(amountEach), posting.units.currency)

        # Income/Expense to be spread
        p1 = data.Posting(account=posting.account,
                          units=amount,
                          cost=None,
                          price=None,
                          flag=None,
                          meta=None)

        # Asset/Liability that buffers the difference
        p2 = data.Posting(account=account,
                          units=mul(amount, D(-1)),
                          cost=None,
                          price=None,
                          flag=None,
                          meta=None)

        e = data.Transaction(date=closing_dates[i],
                             meta=entry.meta,
                             flag='*',
                             payee=entry.payee,
                             narration=entry.narration + ' (Generated by interpolate-spread %d/%d)'%(i+1, duration), # TODO: SUFFIX
                             tags={'spread'}, # TODO: TAG
                             links=entry.links,
                             postings=[p1, p2])
        new_transactions.append(e)
    return new_transactions


def edit_account(entry, p_index, ACCOUNT_INCOME, ACCOUNT_EXPENSES):
    """Modify original entry to replace Income/Expense with Liability/Asset"""
    posting = entry.postings[p_index]
    account = posting.account.split(':')
    if(account[0] == 'Income'):
        side = ACCOUNT_INCOME
    elif(account[0] == 'Expenses'):
        side = ACCOUNT_EXPENSES
    else:
        return False
    account.pop(0)
    account.insert(0, side)
    account = ':'.join(account)
    entry.postings.pop(p_index)
    entry.postings.insert(p_index, data.Posting(
        account=account,
        units=Amount(posting.units.number, posting.units.currency),
        cost=None,
        price=None,
        flag=None,
        meta=None))

    return account

def spread(entries, options_map, config_string):
    """Add depreciation entries for fixed assets.  See module docstring for more
    details and example"""
    errors = []

    ## Parse config and set defaults
    config_obj = eval(config_string, {}, {})
    if not isinstance(config_obj, dict):
        raise RuntimeError("Invalid plugin configuration: should be a single dict.")
    ACCOUNT_INCOME   = config_obj.pop('account_income'  , 'Liabilities:Current')
    ACCOUNT_EXPENSES = config_obj.pop('account_expenses', 'Assets:Current')
    ALIASES_BEFORE   = config_obj.pop('aliases_before'  , ['spreadBefore'])
    ALIASES_AFTER    = config_obj.pop('aliases_after'   , ['spreadAfter', 'spread'])
    ALIAS_SEPERATOR  = config_obj.pop('aliases_after'   , '-')
    DEFAULT_PERIOD   = config_obj.pop('default_period'  , 'Month')
    DEFAULT_METHOD   = config_obj.pop('default_method'  , 'SL')
    MIN_VALUE        = config_obj.pop('min_value'       , 0.05)
    MAX_NEW_TX       = config_obj.pop('max_new_tx'      , 9999)
    SUFFIX           = config_obj.pop('suffix'          , ' (Generated by interpolate-spread)')
    TAG              = config_obj.pop('tag'             , 'spread')
    MIN_VALUE = D(str(MIN_VALUE))

    ## Filter transaction entries that have tag or meta or its posting has meta.
    newEntries = []
    for i, entry in enumerate(entries):
        if hasattr(entry, 'postings'):
            for j, p in enumerate(entry.postings):
                # TODO: ALIASES_BEFORE
                params = check_aliases_posting(ALIASES_AFTER, entry, p) or check_aliases_entry(ALIASES_AFTER, entry, ALIAS_SEPERATOR)
                if not params:
                    continue

                # `entry` is modified within
                new_account = edit_account(entry, j, ACCOUNT_INCOME, ACCOUNT_EXPENSES)
                if not new_account:
                    continue

                start, duration = parse_params(params, entry.date)

                dates = get_dates(start, duration, MAX_NEW_TX)

                if len(dates) > 0:
                    newEntries = newEntries + get_postings(duration, dates, new_account, p, entry, MIN_VALUE)

    return entries + newEntries, errors

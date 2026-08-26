# Account Growth Rule: The $200 Milestone

**Context:** The current bot uses dynamic position sizing (15% risk, which defaults to 0.01 lots on the standard account). 

**Directive:** DO NOT modify the lot size logic, the base risk parameters, or the position sizing architecture. The current system must remain untouched until the MetaTrader 5 account balance reaches exactly **$200.00**.

When the account balance hits **$200.00**, we will update the lot size constraints and risk management parameters to scale properly. Until then, let the bot run and compound on 0.01 lots.

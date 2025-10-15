{
    'name': 'Transfer to Odoo17 with Retry',
    'version': '1.1',
    'author': 'Djakaridja Traore',
    'depends': ['sale', 'account','base_automation','purchase'],
    'data': [
        'views/view.xml',
        'data/sale_order_actions.xml',
        'data/account_invoice_actions.xml',
        'data/purchase_action.xml',
    ],
    'installable': True,
}

from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    external_odoo_base_url = fields.Char(
        string="URL Odoo Externe",
        help="URL du serveur Odoo cible pour synchronisation"
    )

    PARAM_KEY = 'transfer_to_odoo17.external_odoo_base_url'

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        IrConfig = self.env['ir.config_parameter'].sudo()
        res.update(
            external_odoo_base_url=IrConfig.get_param(self.PARAM_KEY, default=''),
        )
        return res

    @api.multi
    def set_values(self):
        super(ResConfigSettings, self).set_values()
        IrConfig = self.env['ir.config_parameter'].sudo()
        IrConfig.set_param(self.PARAM_KEY, self.external_odoo_base_url or '')

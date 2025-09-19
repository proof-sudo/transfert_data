from odoo import models, fields, api
import json
import requests
import logging

_logger = logging.getLogger(__name__)

class SyncQueue(models.Model):
    _name = "sync.queue"
    _description = "Queue pour envoi vers Odoo17"

    model_name = fields.Char(required=True)
    record_id = fields.Integer(required=True)
    payload = fields.Text(required=True)
    state = fields.Selection([
        ('pending', 'Pending'),
        ('done', 'Done'),
        ('failed', 'Failed')
    ], default='pending')
    attempts = fields.Integer(default=0)

    @api.model
    def process_queue(self):
        """Cron job qui réessaie l'envoi des éléments en attente"""
        pending_records = self.search([('state', 'in', ['pending','failed'])])
        for rec in pending_records:
            try:
                rec.attempts += 1
                url = "https://odoo17.example.com/odoo_sync/%s" % rec.model_name
                headers = {"Content-Type": "application/json", "Authorization": "Bearer SECRET_TOKEN"}
                response = requests.post(url, headers=headers, data=rec.payload, timeout=15)
                if response.status_code == 200:
                    rec.state = 'done'
                    _logger.info("✅ Record %s/%s envoyé avec succès après %s tentative(s)", rec.model_name, rec.record_id, rec.attempts)
                else:
                    rec.state = 'failed'
                    _logger.error("❌ Echec %s/%s : %s", rec.model_name, rec.record_id, response.text)
            except Exception as e:
                rec.state = 'failed'
                _logger.exception("⚠️ Exception envoi %s/%s : %s", rec.model_name, rec.record_id, e)

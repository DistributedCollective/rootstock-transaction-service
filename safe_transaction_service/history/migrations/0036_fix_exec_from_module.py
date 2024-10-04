# Generated by Django 3.1.8 on 2021-04-07 11:35
import logging

from django.db import migrations

from gnosis.eth import get_auto_ethereum_client

from ..utils import clean_receipt_log

logger = logging.getLogger(__name__)


def fix_module_transactions(apps, schema_editor):
    InternalTxDecoded = apps.get_model("history", "InternalTxDecoded")
    InternalTxDecoded.objects.filter(
        function_name="execTransactionFromModuleReturnData"
    ).update(processed=False)


def fix_ethereum_logs(apps, schema_editor):
    EthereumTx = apps.get_model("history", "EthereumTx")
    ethereum_client = get_auto_ethereum_client()

    # We need to add `address` to the logs, so we exclude empty logs and logs already containing `address`
    queryset = EthereumTx.objects.exclude(logs__0__has_key="address").exclude(logs=[])
    total = queryset.count()
    processed = 200
    logger.info("Fixing ethereum logs. %d remaining to be fixed", total)
    while True:
        ethereum_txs = queryset[:processed]
        if not ethereum_txs:
            break

        tx_hashes = [ethereum_tx.tx_hash for ethereum_tx in ethereum_txs]
        try:
            tx_receipts = ethereum_client.get_transaction_receipts(tx_hashes)
            for ethereum_tx, tx_receipt in zip(ethereum_txs, tx_receipts):
                ethereum_tx.logs = [
                    clean_receipt_log(log) for log in tx_receipt["logs"]
                ]
                ethereum_tx.save(update_fields=["logs"])
                total -= 1

            logger.info(
                "Fixed %d ethereum logs. %d remaining to be fixed", processed, total
            )
        except IOError:
            logger.warning("Node connection error when retrieving tx receipts")


class Migration(migrations.Migration):
    dependencies = [
        ("history", "0035_safemastercopy_deployer"),
    ]

    operations = [
        #  migrations.RunPython(fix_ethereum_logs, reverse_code=migrations.RunPython.noop),
        #  Use management command `fix_ethereum_logs`
        migrations.RunPython(
            fix_module_transactions, reverse_code=migrations.RunPython.noop
        ),
    ]

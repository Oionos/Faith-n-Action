from django.core.management.base import BaseCommand
from capstone_project.models import blockchain, Block, Donation
from django.utils import timezone
from datetime import datetime
import hashlib
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Tests the blockchain-driven donation system'

    def handle(self, *args, **kwargs):
        self.stdout.write('Testing Blockchain System...\n')
        
        # Test 1: Check blockchain validity
        self.stdout.write('Test 1: Checking blockchain validity...')
        try:
            is_valid = blockchain.is_chain_valid()
            self.stdout.write(self.style.SUCCESS(f'Blockchain is {"VALID" if is_valid else "INVALID"}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Blockchain validity check failed: {str(e)}'))
            logger.error(f"Test 1 failed: {str(e)}")
        self.stdout.write('')

        # Test 2: Check block structure
        self.stdout.write('Test 2: Checking block structure...')
        try:
            chain = blockchain.get_chain()
            self.stdout.write(f'Number of blocks: {len(chain)}')
            if not chain:
                self.stdout.write(self.style.WARNING('No blocks found in the blockchain'))
            for block in chain:
                self.stdout.write(f'Block {block["index"]}:')
                self.stdout.write(f'  - Hash: {block["hash"]}')
                self.stdout.write(f'  - Previous Hash: {block["previous_hash"]}')
                self.stdout.write(f'  - Transactions: {len(block["transactions"])}')
                self.stdout.write(f'  - Proof: {block["proof"]}')
                self.stdout.write(f'  - Timestamp: {block["timestamp"]}')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Block structure check failed: {str(e)}'))
            logger.error(f"Test 2 failed: {str(e)}")
        self.stdout.write('')

        # Test 3: Check pending transactions
        self.stdout.write('Test 3: Checking pending transactions...')
        try:
            pending = blockchain.pending_transactions
            self.stdout.write(f'Number of pending transactions: {len(pending)}')
            if pending:
                for tx in pending:
                    self.stdout.write(f'  - Transaction ID: {tx.get("transaction_id", "N/A")}')
                    self.stdout.write(f'    Donor: {tx.get("donor", "N/A")}')
                    self.stdout.write(f'    Amount: {tx.get("amount", "N/A")}')
                    self.stdout.write(f'    Date: {tx.get("donation_date", "N/A")}')
                    self.stdout.write(f'    Status: {tx.get("status", "N/A")}')
            else:
                self.stdout.write('No pending transactions')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Pending transactions check failed: {str(e)}'))
            logger.error(f"Test 3 failed: {str(e)}")
        self.stdout.write('')

        # Test 4: Check block linking
        self.stdout.write('Test 4: Checking block linking...')
        try:
            for i in range(1, len(chain)):
                current_block = chain[i]
                previous_block = chain[i-1]
                if current_block['previous_hash'] == previous_block['hash']:
                    self.stdout.write(f'Block {current_block["index"]} correctly links to Block {previous_block["index"]}')
                else:
                    self.stdout.write(self.style.ERROR(f'Block {current_block["index"]} has incorrect previous hash!'))
                    logger.error(f"Block {current_block['index']} previous_hash mismatch: {current_block['previous_hash']} != {previous_block['hash']}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Block linking check failed: {str(e)}'))
            logger.error(f"Test 4 failed: {str(e)}")
        self.stdout.write('')

        # Test 5: Check proof of work
        self.stdout.write('Test 5: Checking proof of work...')
        try:
            for block in chain:
                if block['index'] > 1:  # Skip genesis block
                    previous_block = chain[block['index']-2]
                    proof = block['proof']
                    previous_proof = previous_block['proof']
                    hash_operation = hashlib.sha256(str(proof**2 - previous_proof**2).encode()).hexdigest()
                    if hash_operation.startswith('0000'):
                        self.stdout.write(f'Block {block["index"]} has valid proof of work')
                    else:
                        self.stdout.write(self.style.ERROR(f'Block {block["index"]} has invalid proof of work: {hash_operation}'))
                        logger.error(f"Block {block['index']} invalid proof: {hash_operation}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Proof of work check failed: {str(e)}'))
            logger.error(f"Test 5 failed: {str(e)}")
        self.stdout.write('')

        # Test 6: Check transaction integrity
        self.stdout.write('Test 6: Checking transaction integrity...')
        try:
            for block in chain:
                if block['transactions']:
                    self.stdout.write(f'Block {block["index"]} contains {len(block["transactions"])} transactions')
                    for tx in block['transactions']:
                        self.stdout.write(f'  - Transaction ID: {tx.get("transaction_id", "N/A")}')
                        self.stdout.write(f'    Donor: {tx.get("donor", "N/A")}')
                        self.stdout.write(f'    Email: {tx.get("email", "N/A")}')
                        self.stdout.write(f'    Amount: {tx.get("amount", "N/A")}')
                        self.stdout.write(f'    Date: {tx.get("donation_date", "N/A")}')
                        self.stdout.write(f'    Method: {tx.get("payment_method", "N/A")}')
                        self.stdout.write(f'    Status: {tx.get("status", "N/A")}')

                        # Verify donation_date format
                        if 'donation_date' in tx and tx['donation_date']:
                            try:
                                datetime.strptime(tx['donation_date'], '%Y-%m-%d')
                                self.stdout.write(f'    Date format: VALID')
                            except ValueError:
                                self.stdout.write(self.style.ERROR(f'    Date format: INVALID ({tx["donation_date"]})'))
                                logger.error(f"Invalid donation_date in transaction {tx['transaction_id']}: {tx['donation_date']}")

                        # Cross-check with Donation model
                        try:
                            donation = Donation.objects.get(transaction_id=tx['transaction_id'])
                            if donation.status != tx['status']:
                                self.stdout.write(self.style.ERROR(f'    Status mismatch: Donation model ({donation.status}) vs Transaction ({tx["status"]})'))
                                logger.error(f"Status mismatch for {tx['transaction_id']}: {donation.status} != {tx['status']}")
                            if str(donation.amount) != tx['amount']:
                                self.stdout.write(self.style.ERROR(f'    Amount mismatch: Donation model ({donation.amount}) vs Transaction ({tx["amount"]})'))
                                logger.error(f"Amount mismatch for {tx['transaction_id']}: {donation.amount} != {tx['amount']}")
                            if donation.donation_date.isoformat() != tx['donation_date']:
                                self.stdout.write(self.style.ERROR(f'    Date mismatch: Donation model ({donation.donation_date.isoformat()}) vs Transaction ({tx["donation_date"]})'))
                                logger.error(f"Date mismatch for {tx['transaction_id']}: {donation.donation_date.isoformat()} != {tx['donation_date']}")
                        except Donation.DoesNotExist:
                            self.stdout.write(self.style.ERROR(f'    Donation not found in database for Transaction ID: {tx["transaction_id"]}'))
                            logger.error(f"Donation not found for transaction {tx['transaction_id']}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Transaction integrity check failed: {str(e)}'))
            logger.error(f"Test 6 failed: {str(e)}")
        self.stdout.write('')

        # Test 7: Check donation signatures
        self.stdout.write('Test 7: Checking donation signatures...')
        try:
            from django.conf import settings
            PUBLIC_KEY = getattr(settings, 'PUBLIC_KEY', None)
            if not PUBLIC_KEY:
                self.stdout.write(self.style.ERROR('Public key not configured in settings'))
                logger.error("Test 7 failed: Public key not configured")
            else:
                for block in chain:
                    for tx in block['transactions']:
                        try:
                            donation = Donation.objects.get(transaction_id=tx['transaction_id'])
                            if donation.verify_signature(PUBLIC_KEY):
                                self.stdout.write(f'  - Transaction {tx["transaction_id"]}: Signature VALID')
                            else:
                                self.stdout.write(self.style.ERROR(f'  - Transaction {tx["transaction_id"]}: Signature INVALID'))
                                logger.error(f"Invalid signature for transaction {tx['transaction_id']}")
                        except Donation.DoesNotExist:
                            self.stdout.write(self.style.ERROR(f'  - Transaction {tx["transaction_id"]}: Donation not found'))
                            logger.error(f"Donation not found for transaction {tx['transaction_id']}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Donation signature check failed: {str(e)}'))
            logger.error(f"Test 7 failed: {str(e)}")
        self.stdout.write('')

        self.stdout.write(self.style.SUCCESS('Blockchain testing completed!'))
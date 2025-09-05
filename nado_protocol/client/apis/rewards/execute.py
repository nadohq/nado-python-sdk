from typing import Optional
from nado_protocol.contracts.types import (
    ClaimFoundationRewardsContractParams,
    ClaimFoundationRewardsProofStruct,
    ClaimTokensContractParams,
    ClaimTokensParams,
)
from nado_protocol.client.apis.base import NadoBaseAPI
from eth_account.signers.local import LocalAccount

from nado_protocol.utils.exceptions import InvalidTokenClaimParams


class RewardsExecuteAPI(NadoBaseAPI):
    def _validate_claim_params(self, params: ClaimTokensParams):
        p = ClaimTokensParams.parse_obj(params)
        if p.amount is None and p.claim_all is None:
            raise InvalidTokenClaimParams()

    def claim(
        self, params: ClaimTokensParams, signer: Optional[LocalAccount] = None
    ) -> str:
        self._validate_claim_params(params)
        signer = self._get_signer(signer)
        claim_params = self._get_claim_tokens_contract_params(params, signer)
        return self.context.contracts.claim(
            claim_params.epoch,
            claim_params.amount_to_claim,
            claim_params.total_claimable_amount,
            claim_params.merkle_proof,
            signer,
        )

    def claim_and_stake(
        self, params: ClaimTokensParams, signer: Optional[LocalAccount] = None
    ) -> str:
        self._validate_claim_params(params)
        signer = self._get_signer(signer)
        claim_params = self._get_claim_tokens_contract_params(params, signer)
        return self.context.contracts.claim_and_stake(
            claim_params.epoch,
            claim_params.amount_to_claim,
            claim_params.total_claimable_amount,
            claim_params.merkle_proof,
            signer,
        )

    def stake(self, amount: int, signer: Optional[LocalAccount] = None) -> str:
        signer = self._get_signer(signer)
        return self.context.contracts.stake(amount, signer)

    def unstake(self, amount: int, signer: Optional[LocalAccount] = None) -> str:
        signer = self._get_signer(signer)
        return self.context.contracts.unstake(amount, signer)

    def withdraw_unstaked(self, signer: Optional[LocalAccount] = None):
        signer = self._get_signer(signer)
        return self.context.contracts.withdraw_unstaked(signer)

    def claim_usdc_rewards(self, signer: Optional[LocalAccount] = None):
        signer = self._get_signer(signer)
        return self.context.contracts.claim_usdc_rewards(signer)

    def claim_and_stake_usdc_rewards(self, signer: Optional[LocalAccount] = None):
        signer = self._get_signer(signer)
        return self.context.contracts.claim_and_stake_usdc_rewards(signer)

    def claim_foundation_rewards(self, signer: Optional[LocalAccount] = None):
        """
        Claims all available foundation rewards. Foundation rewards are tokens associated with the chain. For example, ARB on Arbitrum.
        """
        signer = self._get_signer(signer)
        claim_params = self._get_claim_foundation_rewards_contract_params(signer)
        return self.context.contracts.claim_foundation_rewards(
            claim_params.claim_proofs, signer
        )

    def _get_claim_tokens_contract_params(
        self, params: ClaimTokensParams, signer: LocalAccount
    ) -> ClaimTokensContractParams:
        epoch_merkle_proofs = self.context.indexer_client.get_token_merkle_proofs(
            signer.address
        ).merkle_proofs[params.epoch]
        total_claimable_amount = int(epoch_merkle_proofs.total_amount)
        if params.amount is not None:
            amount_to_claim = params.amount
        else:
            assert self.context.contracts.airdrop is not None
            amount_claimed = self.context.contracts.airdrop.functions.getClaimed(
                signer.address
            ).call()
            amount_to_claim = total_claimable_amount - amount_claimed[params.epoch]
        return ClaimTokensContractParams(
            epoch=params.epoch,
            amount_to_claim=amount_to_claim,
            total_claimable_amount=total_claimable_amount,
            merkle_proof=epoch_merkle_proofs.proof,
        )

    def _get_claim_foundation_rewards_contract_params(
        self, signer: LocalAccount
    ) -> ClaimFoundationRewardsContractParams:
        assert self.context.contracts.foundation_rewards_airdrop is not None
        claimed = (
            self.context.contracts.foundation_rewards_airdrop.functions.getClaimed(
                signer.address
            ).call()
        )
        merkle_proofs = (
            self.context.indexer_client.get_foundation_rewards_merkle_proofs(
                signer.address
            )
        )
        claim_proofs = []

        for idx, proof in enumerate(merkle_proofs.merkle_proofs):
            if idx == 0:
                # week 0 is invalid
                continue

            total_amount = int(proof.total_amount)

            # There's no partial claim, so find weeks where there's a claimable amount and amt claimed is zero
            if total_amount > 0 and int(claimed[idx]) == 0:
                claim_proofs.append(
                    ClaimFoundationRewardsProofStruct(
                        totalAmount=total_amount, week=idx, proof=proof.proof
                    )
                )

        return ClaimFoundationRewardsContractParams(claim_proofs=claim_proofs)

from nado_protocol.client.apis.base import NadoBaseAPI


class RewardsQueryAPI(NadoBaseAPI):
    def get_claim_and_stake_estimated_vrtx(self, wallet: str) -> int:
        """
        Estimates the amount of USDC -> VRTX swap when claiming + staking USDC rewards
        """
        assert self.context.contracts.vrtx_staking is not None
        return self.context.contracts.vrtx_staking.functions.getEstimatedVrtxToStake(
            wallet
        ).call()

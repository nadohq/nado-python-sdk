from sanity import ENGINE_BACKEND_URL
from nado_protocol.engine_client.types.query import QueryAllProductsParams
from nado_protocol.ws import (
    AllBboStream,
    BestBidOfferStream,
    NadoSubscriptionClient,
    NadoWebSocketClient,
    TradeStream,
)

PRODUCT_ID = 2


def run():
    print("=== /subscribe streaming client ===")
    sub = NadoSubscriptionClient(ENGINE_BACKEND_URL)
    sub.connect(open_timeout=15)
    print("connected to:", sub.url)
    try:
        print("time:", sub.time())
        print("ping:", sub.ping(client_time="0"))

        print(f"subscribing to trade(product_id={PRODUCT_ID})...")
        print("  ack:", sub.subscribe(TradeStream(product_id=PRODUCT_ID)))
        print(f"subscribing to best_bid_offer(product_id={PRODUCT_ID})...")
        print("  ack:", sub.subscribe(BestBidOfferStream(product_id=PRODUCT_ID)))
        print("subscribing to all_bbo...")
        print("  ack:", sub.subscribe(AllBboStream()))

        print("active subscriptions:", sub.list_subscriptions())

        # all_bbo pushes on an interval, so a few events should arrive promptly.
        # (order_update and other private streams require a prior authenticate.)
        print("reading up to 5 pushed events...")
        for _ in range(5):
            try:
                print("  event:", sub.recv(timeout=10))
            except TimeoutError:
                print("  (no event within timeout)")
                break

        print("unsubscribing from all_bbo...")
        print("  ack:", sub.unsubscribe(AllBboStream()))
    finally:
        sub.close()

    print("\n=== /ws query client ===")
    ws = NadoWebSocketClient(ENGINE_BACKEND_URL)
    ws.connect(open_timeout=15)
    print("connected to:", ws.url)
    try:
        resp = ws.query(QueryAllProductsParams())
        status = resp.get("status") if isinstance(resp, dict) else resp
        print("all_products query status:", status)
    finally:
        ws.close()

    print("\nwebsocket sanity complete.")


if __name__ == "__main__":
    run()

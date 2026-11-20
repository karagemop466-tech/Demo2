# refresh-data run diagnostics

- run: https://github.com/karagemop466-tech/Demo2/actions/runs/44727051341
- commit: 75cdfb53ea1d6deb7f8a6158b338b442150f272c
- branch: arena/6836594f-demo2
- finished (UTC): Fri Nov 20 11:22:28 UTC 2026

## Connectivity probe
probe utc: Fri Nov 20 11:22:27 UTC 2026
dns:
44.226.28.91    demo-external-api-nlb-b0adf6094204c0bd.elb.us-west-2.amazonaws.com external-api.demo.kalshi.co
54.71.122.8     demo-external-api-nlb-b0adf6094204c0bd.elb.us-west-2.amazonaws.com external-api.demo.kalshi.co
http:
  status=200 time=0.273664s
  body:
{"cursor":"CgwI1tqA2AYQ4Kaf2gESMktYTVZFQ1JPU1NDQVRFR09SWS1TMjAyNlhBTEdCSURSN1RFV0NJT0EtQVVOTFZCMjMz","markets":[{"can_close_early":true,"close_time":"2026-11-27T03:00:00Z","created_time":"2026-11-20T11:21:58.457692Z","custom_strike":{"Associated Events":"KXARGPREMDIVGAME-26NOV20VELCAB,KXMLSGAME-26NO

## Snapshot harvest
[kalshi-snapshot] base=https://external-api.demo.kalshi.co/trade-api/v2
[kalshi-snapshot] taxonomy categories: 19
[kalshi-snapshot] FAILED: GET ?category=AI&limit=1000 -> HTTP 404 Not Found 404 page not found
exit_code=1

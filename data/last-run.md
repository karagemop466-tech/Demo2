# refresh-data run diagnostics

- run: https://github.com/karagemop466-tech/Demo2/actions/runs/44727148949
- commit: 06bee8afea98618730463d09d57b282f6e8a5e0e
- branch: arena/6836594f-demo2
- finished (UTC): Fri Nov 20 11:23:57 UTC 2026

## Connectivity probe
probe utc: Fri Nov 20 11:23:10 UTC 2026
dns:
54.71.122.8     demo-external-api-nlb-b0adf6094204c0bd.elb.us-west-2.amazonaws.com external-api.demo.kalshi.co
44.226.28.91    demo-external-api-nlb-b0adf6094204c0bd.elb.us-west-2.amazonaws.com external-api.demo.kalshi.co
http:
  status=200 time=0.245578s
  body:
{"cursor":"CgwInNuA2AYQyJW24wESMktYTVZFQ1JPU1NDQVRFR09SWS1TMjAyNjZGUUNRWFRQTDZJNk9IUUgtSENDU0dDQkxI","markets":[{"can_close_early":true,"close_time":"2026-11-26T00:00:00Z","created_time":"2026-11-20T11:23:08.476941Z","custom_strike":{"Associated Events":"KXNCAAMBGAME-26NOV23LBSUFIU,KXNCAAWBGAME-26NO

## Snapshot harvest
[kalshi-snapshot] base=https://external-api.demo.kalshi.co/trade-api/v2
[kalshi-snapshot] taxonomy categories: 19
[kalshi-snapshot] series: 16643
[kalshi-snapshot] series mapped to a topic: 5978
[kalshi-snapshot] 429 on /markets?status=open&limit=1000&cursor=CgwIzMWA2AYQ8InMwwMSGktYQlRDRC0yNk5PVjIxMTItVDY0Nzk5Ljk5; retry in 500ms
[kalshi-snapshot] 429 on /markets?status=open&limit=1000&cursor=CgsIx8WA2AYQwJq6RBIaS1hCVENELTI2Tk9WMjExNC1UNjM3OTkuOTk; retry in 500ms
[kalshi-snapshot] 429 on /markets?status=open&limit=1000&cursor=CgsIwcWA2AYQiN7SJBIWS1hCVEMtMjZOT1YyMTE4LUI2MTc1MA; retry in 500ms
[kalshi-snapshot] 429 on /markets?status=open&limit=1000&cursor=CgwIu8WA2AYQ8MzhgwESFktYQlRDLTI2Tk9WMjEyMC1CNjg0NTA; retry in 500ms
[kalshi-snapshot] 429 on /markets?status=open&limit=1000&cursor=CgwItsWA2AYQ2PzrlAISFEtYQk5CLTI2Tk9WMjEyMy1CNzEy; retry in 500ms
[kalshi-snapshot] 429 on /markets?status=open&limit=1000&cursor=CgwIr8WA2AYQ-MPX3wESF0tYV1RJSC0yNk5PVjIyMjMtVDgwLjk5; retry in 500ms
[kalshi-snapshot] 429 on /markets?status=open&limit=1000&cursor=CgwIo8WA2AYQ4MmjuQESGktYQlRDRC0yNk5PVjI3MTctVDQ4OTk5Ljk5; retry in 500ms
[kalshi-snapshot] 429 on /markets?status=open&limit=1000&cursor=CgwI7cb_1wYQ4OrK0gESKUtYTkJBQVNUUFJPVC0yNk5PVjIwQ0hBQVRMLUFUTEREQU5JRUxTNS04; retry in 500ms
[kalshi-snapshot] open markets: 60000
[kalshi-snapshot] 429 on /markets?status=settled&limit=1000&cursor=CgwI0aL71wYQ6MWD_QISGEtYSFlQRS0yNk5PVjIwMDEtQjYzLjM3NQ; retry in 500ms
[kalshi-snapshot] 429 on /markets?status=settled&limit=1000&cursor=CgwIzKL71wYQ2PHcswMSGEtYSFlQRS0yNk5PVjIwMDMtQjUyLjEyNQ; retry in 500ms
[kalshi-snapshot] 429 on /markets?status=settled&limit=1000&cursor=CgwI7JP71wYQwOSU_QESFUtYRVRILTI2Tk9WMjAwNS1CMTQ0Nw; retry in 500ms
[kalshi-snapshot] 429 on /markets?status=settled&limit=1000&cursor=CgwI3pX51wYQgJqCqwMSGktYRVVSVVNEMTVNLTI2Tk9WMTkyMjE1LTMw; retry in 500ms
[kalshi-snapshot] 429 on /markets?status=settled&limit=1000&cursor=CgwIy__11wYQiN2TxAESJ0tYTkJBUFJBLTI2Tk9WMThNSUxNSUEtTUlBQkFERUJBWU8xMy0zMA; retry in 500ms
[kalshi-snapshot] 429 on /markets?status=settled&limit=1000&cursor=CgsIwP_11wYQ-LnBJRIZS1g3WVJSQVRFSC0xOU5PVjI2MDctVDUwMg; retry in 500ms
[kalshi-snapshot] 429 on /markets?status=settled&limit=1000&cursor=CgsIuv_11wYQmIvOUxIZS1hTT0xELTI2Tk9WMTkwOS1UOTIuNDk5OQ; retry in 500ms
[kalshi-snapshot] settled markets: 60000
[kalshi-snapshot] 429 on /events?status=open&limit=200&with_nested_markets=false&cursor=CgYI4I2G_QYSGktYU1RBVEVMRUdXSS0yOE5PVjA3V0lIMDI0; retry in 500ms
[kalshi-snapshot] 429 on /events?status=open&limit=200&with_nested_markets=false&cursor=CgYI4I2G_QYSGktYU1RBVEVMRUdTRC0yOE5PVjA3U0RTMDI0; retry in 500ms
[kalshi-snapshot] 429 on /events?status=open&limit=200&with_nested_markets=false&cursor=CgYI4I2G_QYSGktYU1RBVEVMRUdPSC0yOE5PVjA3T0hIMDUz; retry in 500ms
[kalshi-snapshot] 429 on /events?status=open&limit=200&with_nested_markets=false&cursor=CgYI4I2G_QYSGktYU1RBVEVMRUdOQy0yOE5PVjA3TkNTMDI5; retry in 500ms
[kalshi-snapshot] 429 on /events?status=open&limit=200&with_nested_markets=false&cursor=CgYI4I2G_QYSGktYU1RBVEVMRUdNRS0yOE5PVjA3TUVIMDg0; retry in 500ms
[kalshi-snapshot] 429 on /events?status=open&limit=200&with_nested_markets=false&cursor=CgYI4I2G_QYSGktYU1RBVEVMRUdJTi0yOE5PVjA3SU5IMDkw; retry in 500ms
[kalshi-snapshot] 429 on /events?status=open&limit=200&with_nested_markets=false&cursor=CgYI4I2G_QYSGktYU1RBVEVMRUdGTC0yOE5PVjA3RkxIMTE2; retry in 500ms
[kalshi-snapshot] 429 on /events?status=open&limit=200&with_nested_markets=false&cursor=CgYI4I2G_QYSGktYU1RBVEVMRUdBUi0yOE5PVjA3QVJIMDg1; retry in 500ms
[kalshi-snapshot] 429 on /events?status=open&limit=200&with_nested_markets=false&cursor=CgYI8IjS-AYSE0tYQVVESVRPUlJBQ0UtUEEtMjg; retry in 500ms
[kalshi-snapshot] 429 on /events?status=open&limit=200&with_nested_markets=false&cursor=CgYI4NLt7AYSGktYU1RBVEVMRUdMQS0yN09DVDA5TEFIMDgy; retry in 500ms
[kalshi-snapshot] 429 on /events?status=open&limit=200&with_nested_markets=false&cursor=CgYI8MLe6AYSDktYR09MRk1BSk9SLTI3; retry in 500ms
[kalshi-snapshot] 429 on /events?status=open&limit=200&with_nested_markets=false&cursor=CgYI8NSs5gYSE0tYTUlEVEVSTU1PVi1HQVNFTkQ; retry in 500ms
[kalshi-snapshot] 429 on /events?status=open&limit=200&with_nested_markets=false&cursor=CgYI4KGZ4QYSEktYTkJBTUFUQ0hVUC0yN1dDRg; retry in 500ms
[kalshi-snapshot] 429 on /events?status=open&limit=200&with_nested_markets=false&cursor=CgYI4LC53QYSEEtYQ09OQ0FDQUZOTC0yN0I; retry in 500ms
[kalshi-snapshot] 429 on /events?status=open&limit=200&with_nested_markets=false&cursor=CgYIlJel2wYSDktYR1JBTU1ZLUJJQzY5; retry in 500ms
[kalshi-snapshot] 429 on /events?status=open&limit=200&with_nested_markets=false&cursor=CgYI8ND-2QYSFEtYUkFURVBBWUVSTEFXLTI2U0VQ; retry in 500ms
[kalshi-snapshot] 429 on /events?status=open&limit=200&with_nested_markets=false&cursor=CgYI8MTp2QYSJUtYVk9URUdFTkVSQUwtS1hIT1VTRVJBQ0UtTUEwMy0yNkxUUkE; retry in 500ms
[kalshi-snapshot] open events: 12000
[kalshi-snapshot] in-scope open markets: 0
[kalshi-snapshot] in-scope settled markets: 0
[kalshi-snapshot] orderbooks: 0
[kalshi-snapshot] wrote /home/runner/work/Demo2/Demo2/data/meta.json
[kalshi-snapshot] wrote /home/runner/work/Demo2/Demo2/data/taxonomy.json
[kalshi-snapshot] wrote /home/runner/work/Demo2/Demo2/data/open-markets.json
[kalshi-snapshot] wrote /home/runner/work/Demo2/Demo2/data/open-events.json
[kalshi-snapshot] wrote /home/runner/work/Demo2/Demo2/data/settled-markets.json
[kalshi-snapshot] wrote /home/runner/work/Demo2/Demo2/data/orderbooks.json
[kalshi-snapshot] done in 46879ms (233 requests)
exit_code=0

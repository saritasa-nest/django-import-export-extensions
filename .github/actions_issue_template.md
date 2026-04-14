---
title: "{{ env.ACTION_NAME }}: scheduled action failed"
labels: bug
---
Latest fail located [here]({{ env.LATEST_FAIL }})

To receive notifications about failures: add slack bot to ci chat of your
project and run this

```bash
/github subscribe saritasa-nest/ issues
```

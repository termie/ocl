#!/bin/sh
mitmdump -ns to_requests.py -r $1 -q > $1.json

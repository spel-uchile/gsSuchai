#!/bin/bash

DATE=`date +'%d-%m-%Y'`
ROOT=`pwd`
mongodump --db suchai1_tel_database --out $ROOT/$DATE.dump

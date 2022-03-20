#!/bin/bash

set -e

# extract polybench sources
echo "Extracting polybench sources"
POLYBENCH_SRC_DIR=polybench-c-4.2
if [ -d "$POLYBENCH_SRC_DIR" ]; then
    echo "polybench sources already exist in target folder $POLYBENCH_SRC_DIR -- aborting";
    exit 1;
fi
tar -xzf polybench-c-4.2.tar.gz
cd polybench-c-4.2 || exit 1

# generate trimmed, easily-usable sources
echo "Converting to macro-free sources"
PARGS="-I utilities -DPOLYBENCH_USE_C99_PROTO"
PROCESSED_SRC_DIR=processed
TEMP_PREFIX=tmp_
mkdir $PROCESSED_SRC_DIR
for i in `cat utilities/benchmark_list`; do
    KERNEL=$(basename $i .c)
    echo "processing kernel $KERNEL";
    perl utilities/create_cpped_version.pl $i "$PARGS";
    mv $(dirname $i)/$(basename $i .c).preproc.c $PROCESSED_SRC_DIR/$KERNEL.orig.c
    # while read -r line; do
        # echo -e "$line\n"
    # done <$file
    # TMP_FILE_NAME=$(dirname $i)/tmp_$(basename $i);
    # cat utilities/polybench.c $i > $TMP_FILE_NAME;
    # gcc -I utilities -I $(dirname $i) utilities/polybench.c $TMP_FILE_NAME -E > $PROCESSED_SRC_DIR/$(basename $i);
    # gcc -I utilities -I $(dirname $i) utilities/polybench.c $i -E > $PROCESSED_SRC_DIR/$(basename $i);
    # gcc -I utilities -I $(dirname $i) utilities/polybench.c $i;
done

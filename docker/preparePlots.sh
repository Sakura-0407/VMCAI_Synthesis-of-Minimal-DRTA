#!/bin/bash
function parse() {
        setting=$1
        table=`echo "${setting}" | sed 's/-/_/g'`
        file=`ls -1 results/${setting}.2*.txt 2>/dev/null | tail -n 1`
        if [ "$file" ]; then
                ./parseResults.pl $table $file
        fi
}

echo -n "Copying submission logs... "
cp -r logs-submission/* results/
echo "done"
for tool in rt{a,i}; do
        parse "${tool}"
done

echo -n "Generating tables... "
cd tables
cat queries.sql | sqlite3
cd ..
echo "done"

echo -n "Generating plots... "
cp tikz-source/* plots/
cd plots
sed -i "s/RTADATA/`cat boxes_rta.data`/" states.tex
sed -i "s/RTIDATA/`cat boxes_rti.data`/" states.tex
pdflatex -interaction=nonstopmode states.tex 1>/dev/null 2>&1
pdflatex -interaction=nonstopmode scatter_samples_states.tex 1>/dev/null 2>&1
rm *.tex *.data *.csv *.log *.aux
cd ..
echo "done"

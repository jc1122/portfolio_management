#!/bin/bash
set -e
echo 'Creating fixture directories...
'mkdir -p tests/fixtures/stooq
mkdir -p tests/fixtures/tradeable_instruments

echo 'Copying Stooq data files...
'mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/1/lpg.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/hqy.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/arcb.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/2/ogn.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/cert.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse stocks
cp data/stooq/d_uk_txt/data/daily/uk/lse stocks/can.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse stocks/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/1/bbai.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/otly.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/btct.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nysemkt stocks
cp data/stooq/d_us_txt/data/daily/us/nysemkt stocks/asm.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nysemkt stocks/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/1/fvrr.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/iart.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/2/plnt.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/1/levi.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/3
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/3/zm.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/3/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse stocks
cp data/stooq/d_uk_txt/data/daily/uk/lse stocks/cch.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse stocks/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/dtst.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/1/ddd.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/1/acco.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/3
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/3/ufpi.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/3/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/iosp.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/oss.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/asps.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/spok.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/mara.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/crsp.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/khc.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/ptct.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/kids.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/1/amh.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/livn.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/fbio.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/1/ftv.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/2/t.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/3
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/3/vera.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/3/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nysemkt stocks
cp data/stooq/d_us_txt/data/daily/us/nysemkt stocks/imo.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nysemkt stocks/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/2/mt.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/ifbd.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/agio.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/2/twlo.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/mq.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/mktx.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/1/are.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse stocks
cp data/stooq/d_uk_txt/data/daily/uk/lse stocks/php.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse stocks/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse stocks intl/2
cp data/stooq/d_uk_txt/data/daily/uk/lse stocks intl/2/ltod.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse stocks intl/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/arvn.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/sym.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/sbgi.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/mnmd.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/osur.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/odd.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/bivi.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/1/hnge.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/1/dea.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/2/m.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/ntrb.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/2/ul.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/2/pfsi.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/1/hlf.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/1/cbz.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/eols.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/
mkdir -p tests/fixtures/stooq/d_pl_txt/data/daily/pl/nc stocks
cp data/stooq/d_pl_txt/data/daily/pl/nc stocks/exm.txt tests/fixtures/stooq/d_pl_txt/data/daily/pl/nc stocks/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/1/ifn.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse stocks
cp data/stooq/d_uk_txt/data/daily/uk/lse stocks/bbox.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse stocks/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/2
cp data/stooq/d_uk_txt/data/daily/uk/lse etfs/2/midd.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/2/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse stocks
cp data/stooq/d_uk_txt/data/daily/uk/lse stocks/hmso.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse stocks/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/finw.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/anss.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/3
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/3/xp.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/3/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/1/gwh.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/1/abbv.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/2/o.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/1/aon.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/drs.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/ozk.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/kros.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/2
cp data/stooq/d_uk_txt/data/daily/uk/lse etfs/2/mst3.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/cccs.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/dbx.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/jakk.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/agen.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/2/pm.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/1/enic.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/cdna.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/crnc.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/axti.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/smlr.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/2/net.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse stocks
cp data/stooq/d_uk_txt/data/daily/uk/lse stocks/ao.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse stocks/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/kplt.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/edit.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/1/chd.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/fang.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/2/pack.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/lyft.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/1/ccj.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/ewtx.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/1/bwa.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/2/vici.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/shls.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/gpre.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/anip.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/fosl.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/lmfa.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/2/sbh.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/nukk.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/2/pvl.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/celc.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/2/msc.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/3
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/3/wix.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/3/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/2/sony.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/lbtya.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/1/hp.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/apyx.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse stocks
cp data/stooq/d_uk_txt/data/daily/uk/lse stocks/rr.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse stocks/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/1
cp data/stooq/d_uk_txt/data/daily/uk/lse etfs/1/idvy.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/mny.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/iova.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/2/npki.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/1/cxt.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/hlmn.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/2/shak.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/2/mlm.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/1/fg.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/gogl.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/2/tse.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/1/bak.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/tmdx.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/tcbi.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/2/ritm.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/ccb.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/angi.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/amtx.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/aapl.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/2/rezi.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse stocks
cp data/stooq/d_uk_txt/data/daily/uk/lse stocks/jup.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse stocks/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/bry.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/swvl.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/ssys.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nysemkt stocks
cp data/stooq/d_us_txt/data/daily/us/nysemkt stocks/apt.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nysemkt stocks/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/1/ir.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/3
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/3/wdfc.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/3/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/2/skx.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/2/wds.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/2/ora.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/2/tdc.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/1/aap.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/ke.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/1
cp data/stooq/d_uk_txt/data/daily/uk/lse etfs/1/fb3.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/1/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/1
cp data/stooq/d_uk_txt/data/daily/uk/lse etfs/1/ecom.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/1/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/2
cp data/stooq/d_uk_txt/data/daily/uk/lse etfs/2/xuhy.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/2/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/2
cp data/stooq/d_uk_txt/data/daily/uk/lse etfs/2/sxlk.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/2/mdt.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/2/unh.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/1/an.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/2/xom.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/1
cp data/stooq/d_uk_txt/data/daily/uk/lse etfs/1/anxu.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/himx.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/2
cp data/stooq/d_uk_txt/data/daily/uk/lse etfs/2/vdnr.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/2/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/1
cp data/stooq/d_uk_txt/data/daily/uk/lse etfs/1/2pal.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/1/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse stocks
cp data/stooq/d_uk_txt/data/daily/uk/lse stocks/adt1.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse stocks/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/meli.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse stocks
cp data/stooq/d_uk_txt/data/daily/uk/lse stocks/lgen.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse stocks/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/1/ball.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/1/dht.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/2/x.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/1
cp data/stooq/d_uk_txt/data/daily/uk/lse etfs/1/3uss.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/1/grbk.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/2
cp data/stooq/d_uk_txt/data/daily/uk/lse etfs/2/vdta.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/2/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/2
cp data/stooq/d_uk_txt/data/daily/uk/lse etfs/2/jepg.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/1/grmn.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/cost.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/1/dsx.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/aep.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/mlco.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse stocks
cp data/stooq/d_uk_txt/data/daily/uk/lse stocks/ufo.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse stocks/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/1/ax.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/qcom.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/1
cp data/stooq/d_uk_txt/data/daily/uk/lse etfs/1/arm3.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/1/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/2
cp data/stooq/d_uk_txt/data/daily/uk/lse etfs/2/jepi.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/1/cvs.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/1/ice.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/atec.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/1
cp data/stooq/d_uk_txt/data/daily/uk/lse etfs/1/amz3.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/1/hpp.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/1/clx.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/1/glw.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/2
cp data/stooq/d_uk_txt/data/daily/uk/lse etfs/2/tip5.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/avgo.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/2
cp data/stooq/d_uk_txt/data/daily/uk/lse etfs/2/xmed.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/1/gpc.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/1/cof.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/1
cp data/stooq/d_uk_txt/data/daily/uk/lse etfs/1/buyb.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/2/v.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse stocks intl/2
cp data/stooq/d_uk_txt/data/daily/uk/lse stocks intl/2/gtco.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse stocks intl/2/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/1
cp data/stooq/d_uk_txt/data/daily/uk/lse etfs/1/gld3.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/2/main.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/1
cp data/stooq/d_uk_txt/data/daily/uk/lse etfs/1/itek.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/1/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/2
cp data/stooq/d_uk_txt/data/daily/uk/lse etfs/2/vdty.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/1/abt.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/1/gtls.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/2
cp data/stooq/d_uk_txt/data/daily/uk/lse etfs/2/mweq.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/2/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/1
cp data/stooq/d_uk_txt/data/daily/uk/lse etfs/1/emad.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/1/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/1
cp data/stooq/d_uk_txt/data/daily/uk/lse etfs/1/bnks.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/2/tnk.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/2
cp data/stooq/d_uk_txt/data/daily/uk/lse etfs/2/sdig.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/2/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/1
cp data/stooq/d_uk_txt/data/daily/uk/lse etfs/1/3usl.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/1/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/2
cp data/stooq/d_uk_txt/data/daily/uk/lse etfs/2/nvdi.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/2/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/1
cp data/stooq/d_uk_txt/data/daily/uk/lse etfs/1/iumo.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/3
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/3/wprt.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/3/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/1
cp data/stooq/d_uk_txt/data/daily/uk/lse etfs/1/fsky.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/1/jnj.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/achv.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/2/trno.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/1/ipg.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/centa.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/1/gap.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/1
cp data/stooq/d_uk_txt/data/daily/uk/lse etfs/1/alum.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/1/amrc.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse stocks
cp data/stooq/d_uk_txt/data/daily/uk/lse stocks/eml.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse stocks/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/1
cp data/stooq/d_uk_txt/data/daily/uk/lse etfs/1/idna.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/irix.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/2/usb.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/1
cp data/stooq/d_uk_txt/data/daily/uk/lse etfs/1/geny.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/1/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/1
cp data/stooq/d_uk_txt/data/daily/uk/lse etfs/1/cndx.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/gild.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/2/mo.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/2
cp data/stooq/d_uk_txt/data/daily/uk/lse etfs/2/vhve.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/2/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/2
cp data/stooq/d_uk_txt/data/daily/uk/lse etfs/2/ssln.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/2/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/2
cp data/stooq/d_uk_txt/data/daily/uk/lse etfs/2/vwra.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/2/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/2
cp data/stooq/d_uk_txt/data/daily/uk/lse etfs/2/vdev.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/2/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/1
cp data/stooq/d_uk_txt/data/daily/uk/lse etfs/1/hyus.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/mmyt.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/ehth.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/2
cp data/stooq/d_uk_txt/data/daily/uk/lse etfs/2/wcld.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/2/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/1
cp data/stooq/d_uk_txt/data/daily/uk/lse etfs/1/3des.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/1/kbh.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/1/iff.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/rcat.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/avav.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/pcrx.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/2
cp data/stooq/d_uk_txt/data/daily/uk/lse etfs/2/lpla.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/asmb.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/1/bk.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/1
cp data/stooq/d_uk_txt/data/daily/uk/lse etfs/1/isac.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/1/lumn.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/hson.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/2/sb.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/2/sre.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/omab.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/1/azo.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/2/mco.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse stocks
cp data/stooq/d_uk_txt/data/daily/uk/lse stocks/sge.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse stocks/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/2/vz.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/2/ma.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/2
cp data/stooq/d_uk_txt/data/daily/uk/lse etfs/2/scop.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/2/r.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/2/syk.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/1
cp data/stooq/d_uk_txt/data/daily/uk/lse etfs/1/iuaa.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/1/lrn.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/2
cp data/stooq/d_uk_txt/data/daily/uk/lse etfs/2/rtys.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/2/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/1
cp data/stooq/d_uk_txt/data/daily/uk/lse etfs/1/3brl.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/1/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse stocks
cp data/stooq/d_uk_txt/data/daily/uk/lse stocks/cgo.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse stocks/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/2
cp data/stooq/d_uk_txt/data/daily/uk/lse etfs/2/smh.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/2/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse stocks
cp data/stooq/d_uk_txt/data/daily/uk/lse stocks/som.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse stocks/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/1
cp data/stooq/d_uk_txt/data/daily/uk/lse etfs/1/bbtr.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/1/c.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/clne.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/tmus.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/gbdc.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/3
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/3/vrsn.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/3/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/1
cp data/stooq/d_uk_txt/data/daily/uk/lse etfs/1/asdv.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/1/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/2
cp data/stooq/d_uk_txt/data/daily/uk/lse etfs/2/vapx.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/2/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse stocks
cp data/stooq/d_uk_txt/data/daily/uk/lse stocks/rrr.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse stocks/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse stocks
cp data/stooq/d_uk_txt/data/daily/uk/lse stocks/aaz.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse stocks/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/2
cp data/stooq/d_uk_txt/data/daily/uk/lse etfs/2/tswe.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/2/nke.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/1
cp data/stooq/d_uk_txt/data/daily/uk/lse etfs/1/imib.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nysemkt stocks
cp data/stooq/d_us_txt/data/daily/us/nysemkt stocks/tovx.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nysemkt stocks/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/2/mrk.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse stocks
cp data/stooq/d_uk_txt/data/daily/uk/lse stocks/dge.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse stocks/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/2
cp data/stooq/d_uk_txt/data/daily/uk/lse etfs/2/uspy.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/jazz.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/2/peg.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/1/ibm.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/aray.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/2/nyt.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/2/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/1
cp data/stooq/d_uk_txt/data/daily/uk/lse etfs/1/floa.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/1/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse stocks
cp data/stooq/d_uk_txt/data/daily/uk/lse stocks/w7l.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse stocks/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1
cp data/stooq/d_us_txt/data/daily/us/nyse stocks/1/efx.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nyse stocks/1/
mkdir -p tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1
cp data/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/hon.us.txt tests/fixtures/stooq/d_us_txt/data/daily/us/nasdaq stocks/1/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/1
cp data/stooq/d_uk_txt/data/daily/uk/lse etfs/1/cnya.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/1/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/1
cp data/stooq/d_uk_txt/data/daily/uk/lse etfs/1/iuis.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/1/
mkdir -p tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/2
cp data/stooq/d_uk_txt/data/daily/uk/lse etfs/2/msf3.uk.txt tests/fixtures/stooq/d_uk_txt/data/daily/uk/lse etfs/2/

echo 'Creating tradeable instrument fixture files...
'

import sys, json; sys.path.insert(0,"/tmp/claude-0/-home-user-cerberusdao/4a2ff1f8-cae0-559f-aeff-0cc47fe07ff5/scratchpad/tools")
from chain import call, get_balance
R={}
TOKEN="0x8a14897ea5f668f36671678593fae44ae23b39fb"
TREAS="0x56d595ea5591d264bc1ef9e073af66685f0bfd31"
STAK="0x95deaf8dd30380acd6cc5e4e90e5eef94d258854"
SOHM="0xa552f061d8962be4c1f6bc6b0403ca620f569330"
DIST="0x3878db57d6e1c15a3670d32ed15d3853bd5c6fde"
WARM="0x63548e4894ee26e08eda08145c57ecda09cfe74a"
SHIB="0x95ad61b0a150d79219dcf64e1e6cc01f0b64c4ce"; WETH="0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
FLOKI="0x43f11c02439e2736800433b4594994bd43cd066d"; LP="0xb5b6c3816c66fa6bc5b189f49e5b088e2de5082a"
BONDS={"SHIB":"0x5f50d0f427228f48665fb790685c450328995c0d","LP":"0xd2e0bd64b3e6fbc4d09f9a11e5852bf9a46a6731",
       "WETH":"0x30f5039447b8aef529db99324896b14d453d85fa","FLOKI":"0xf0c2b0ec587155abe978ae47705f0c619f44bc65"}
R["token_owner"]=call(TOKEN,"owner()(address)"); R["token_vault"]=call(TOKEN,"vault()(address)")
R["token_totalSupply"]=call(TOKEN,"totalSupply()(uint256)")
R["treasury_manager"]=call(TREAS,"manager()(address)")
R["treasury_totalReserves"]=call(TREAS,"totalReserves()(uint256)")
R["treasury_totalDebt"]=call(TREAS,"totalDebt()(uint256)")
R["treasury_excessReserves"]=call(TREAS,"excessReserves()(uint256)")
R["staking_manager"]=call(STAK,"manager()(address)"); R["staking_warmupPeriod"]=call(STAK,"warmupPeriod()(uint256)")
R["staking_totalBonus"]=call(STAK,"totalBonus()(uint256)"); R["staking_distributor"]=call(STAK,"distributor()(address)")
R["staking_locker"]=call(STAK,"locker()(address)")
ep=call(STAK,"epoch()(uint256,uint256,uint256,uint256)",rettypes=["uint256"]*4)
R["staking_epoch"]={"length":ep[0],"number":ep[1],"endBlock":ep[2],"distribute":ep[3]} if ep else None
R["sohm_manager"]=call(SOHM,"manager()(address)"); R["sohm_stakingContract"]=call(SOHM,"stakingContract()(address)")
R["sohm_index"]=call(SOHM,"index()(uint256)"); R["sohm_totalSupply"]=call(SOHM,"totalSupply()(uint256)")
R["sohm_INDEX"]=call(SOHM,"INDEX()(uint256)")
R["dist_manager"]=call(DIST,"manager()(address)"); R["dist_epochLength"]=call(DIST,"epochLength()(uint256)")
R["dist_nextEpochBlock"]=call(DIST,"nextEpochBlock()(uint256)")
di=call(DIST,"info(uint256)(uint256,address)",0,argtypes=["uint256"],rettypes=["uint256","address"])
R["dist_info0"]={"rate":di[0],"recipient":di[1]} if di else None
adj=call(DIST,"adjustments(uint256)(bool,uint256,uint256)",0,argtypes=["uint256"],rettypes=["bool","uint256","uint256"])
R["dist_adjust0"]={"add":adj[0],"rate":adj[1],"target":adj[2]} if adj else None
R["bonds"]={}
for k,a in BONDS.items():
    t=call(a,"terms()(uint256,uint256,uint256,uint256,uint256,uint256)",rettypes=["uint256"]*6)
    e={"address":a,"principal":k}
    if t: e["terms"]={"controlVariable":t[0],"vestingTerm":t[1],"minimumPrice":t[2],"maxPayout":t[3],"fee":t[4],"maxDebt":t[5]}
    e["totalDebt"]=call(a,"totalDebt()(uint256)"); e["currentDebt"]=call(a,"currentDebt()(uint256)")
    e["bondPriceInUSD"]=call(a,"bondPriceInUSD()(uint256)"); e["maxPayout"]=call(a,"maxPayout()(uint256)")
    e["debtRatio"]=call(a,"debtRatio()(uint256)"); e["manager"]=call(a,"manager()(address)")
    R["bonds"][k]=e
R["treasury_bal_SHIB"]=call(SHIB,"balanceOf(address)(uint256)",TREAS)
R["treasury_bal_WETH"]=call(WETH,"balanceOf(address)(uint256)",TREAS)
R["treasury_bal_FLOKI"]=call(FLOKI,"balanceOf(address)(uint256)",TREAS)
R["treasury_bal_LP"]=call(LP,"balanceOf(address)(uint256)",TREAS)
R["treasury_bal_3DOG"]=call(TOKEN,"balanceOf(address)(uint256)",TREAS)
R["treasury_eth"]=get_balance(TREAS)
R["staking_bal_3DOG"]=call(TOKEN,"balanceOf(address)(uint256)",STAK)
R["warmup_bal_sOHM"]=call(SOHM,"balanceOf(address)(uint256)",WARM)
lp_r=call(LP,"getReserves()(uint112,uint112,uint32)",rettypes=["uint112","uint112","uint32"])
R["lp_reserves"]={"reserve0_3DOG":lp_r[0],"reserve1_WETH":lp_r[1],"ts":lp_r[2]} if lp_r else None
R["lp_totalSupply"]=call(LP,"totalSupply()(uint256)")
R["lp_bal_3DOG"]=call(TOKEN,"balanceOf(address)(uint256)",LP)
R["lp_bal_WETH"]=call(WETH,"balanceOf(address)(uint256)",LP)
R["master_bal_3DOG"]=call(TOKEN,"balanceOf(address)(uint256)","0xdb00139222c99e9098def2cebcd94bdcda8e7625")
R["master_bal_LP"]=call(LP,"balanceOf(address)(uint256)","0xdb00139222c99e9098def2cebcd94bdcda8e7625")
R["master_bal_sOHM"]=call(SOHM,"balanceOf(address)(uint256)","0xdb00139222c99e9098def2cebcd94bdcda8e7625")
R["master_eth"]=get_balance("0xdb00139222c99e9098def2cebcd94bdcda8e7625")
json.dump(R, open("/tmp/claude-0/-home-user-cerberusdao/4a2ff1f8-cae0-559f-aeff-0cc47fe07ff5/scratchpad/state.json","w"), indent=2)
print(json.dumps(R, indent=2))

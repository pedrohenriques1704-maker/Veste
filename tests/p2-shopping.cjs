const fs=require('node:fs');
const assert=require('node:assert/strict');
const s=fs.readFileSync(require('node:path').join(__dirname,'..','app.js'),'utf8');
const core=s.slice(s.indexOf("  const GROUPS"),s.indexOf("  const $ ="));
const discovery=s.slice(s.indexOf("function discoveryFeature(){"),s.indexOf("  const TRASH_WINDOW"));
const factory=new Function(core+"const state={pieces:[],settings:{prefs:['casual'],v3:{ratings:{}},avoidPairs:[],favorites:[]}};const escapeHTML=s=>String(s).replace(/</g,'&lt;');const isDemoPiece=p=>!!p.demo;const shoppingProfile=()=>({learned:{casual:3},observed:6});"+discovery+"return {d:discoveryFeature(),state};");
const {d,state}=factory();
const p=(id,group,color,name,extras={})=>({id,group,color,name,styles:['casual'],available:true,...extras});
const a=p("x","top","bege","Camisa de linho",{source:"catalog",price:100,occasion:["casual"],url:"https://www.awin1.com/pclick.php?p=123"}),b=p("b","bottom","preto","Calça"),c=p("c","shoes","marrom","Sapato"),layer=p("d","layer","marinho","Blazer");
state.pieces=[b,c,layer];
const model={learned:{casual:3},observed:6},val=(q=a,closet=state.pieces)=>d.shop.purchaseValue(q,closet,model);
const cases=[
["match and cost",()=>val().combos===1&&val().cost===100],
["unknown price",()=>val({...a,price:null}).cost===null],
["empty closet",()=>val(a,[]).score===null],
["unknown color",()=>val({...a,color:""}).score===null],
["duplicate penalty",()=>val(a,[b,c,layer,p("dup","top","bege","Camisa de linho")]).score<val().score],
["exclude demo / deleted / unavailable",()=>val(a,[p("d2","bottom","preto","demo",{demo:true}),p("e","bottom","preto","deleted",{deletedAt:"2026-11-01"}),p("f","bottom","preto","unavailable",{available:false}),c]).combos===0],
["blocked colors",()=>{state.settings.avoidPairs=["bege|preto"];const n=val().combos;state.settings.avoidPairs=[];return n===0}],
["onepiece no closet",()=>d.shop.purchaseLooks(p("z","onepiece","preto","Vestido"),[]).length===0],
["shoe candidate",()=>val(c,[a,b]).combos===1],
["accessory candidate",()=>val(p("z","accessory","preto","Bolsa"),[a,b,c]).combos===1],
["score range",()=>val().score>=0&&val().score<=100],
["no complement cap",()=>val(a,[p("q","top","bege","Camisa")]).score<=45],
["valid product",()=>d.normalize({name:"Camisa",group:"top",url:"https://example.com",price:"129,90"}).price===129.9],
["unsafe product link",()=>d.normalize({name:"Camisa",url:"javascript:alert(1)"})===null],
["availability false survives normalization",()=>d.normalize({...a,offerAvailable:false}).offerAvailable===false],
["syntax",()=>{new Function(s);return true}],
];
const data={votes:[{liked:true,id:a.id,item:a}],tracks:[]};d.shop.seed(data,a,"2026-11-01");
cases.push(["price drop",()=>d.shop.update(data,[{...a,price:80}],"2026-11-02")===1&&d.shop.signal(data.tracks[0]).drop===20],["price target",()=>{data.tracks[0].target=90;return d.shop.signal(data.tracks[0]).goal}],["same price dedup",()=>d.shop.update(data,[{...a,price:80}],"2026-11-03")===0&&data.tracks[0].history.length===2],["missing price stays",()=>d.shop.update(data,[{...a,price:null}],"2026-11-04")===0&&data.votes[0].item.price===80],["unavailable does not create a false alert",()=>d.shop.update(data,[{...a,price:25,offerAvailable:false}],"2026-11-05")===0&&data.tracks[0].history.length===2&&data.votes[0].item.offerAvailable===false]);
for(const [name,fn] of cases){assert.ok(fn(),name);console.log("PASS",name)}
console.log(cases.length+" checks passed");

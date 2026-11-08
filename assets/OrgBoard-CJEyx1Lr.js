import{r as d,j as e}from"./react-8qEOpjgC.js";
import{q as Ns,B as es}from"./index-BTpksmUe.js";
import{p as ys,f as $s,h as Ye,a as Ms,C as xe}from"./providers-DnJ_MwcM.js";
import{P as people}from"./record-C1XnZDk6.js";
import"./router-w_hgs3_5.js";
import"./vendor-CgWgUbtC.js";

/* Card width is chosen at layout time so a phone gets one full-width column
   and a desktop row stays wide enough for names. The existing child cap
   (xe, currently 50, paged from le) is unchanged. */
const GAP=32,VGAP=52,ROWGAP=22,me=800;
const le=Math.min(40,xe);
const ICONS={root:"◎",group:"▦",org:"⬢",seat:"◉",body:"⬡"};

function normName(s){
  return String(s||"").toLowerCase().replace(/\./g,"").replace(/\b(jr|sr|ii|iii|iv)\b/g,"").replace(/[^a-z\s'-]/g," ").replace(/\s+/g," ").trim();
}
function firstLast(s){
  const p=normName(s).split(" ").filter(Boolean);
  if(!p.length)return"";
  return p.length===1?p[0]:`${p[0]} ${p[p.length-1]}`;
}
const photoByKey=new Map,ambiguous=new Set;
function addKey(k,person){
  if(!k||!person.photoUrl||ambiguous.has(k))return;
  const prev=photoByKey.get(k);
  if(prev&&prev!==person){photoByKey.delete(k);ambiguous.add(k);return}
  photoByKey.set(k,person);
}
for(const person of people){
  if(!person?.photoUrl||!person.name)continue;
  addKey(normName(person.name),person);
  const fl=firstLast(person.name);
  if(fl!==normName(person.name))addKey(fl,person);
}
function portraitOf(name){
  if(!name)return null;
  return photoByKey.get(normName(name))||photoByKey.get(firstLast(name))||null;
}
function initials(name){
  const p=String(name||"").replace(/\b(Jr|Sr|II|III|IV)\.?$/i,"").split(/\s+/).filter(w=>/^[A-Za-z]/.test(w));
  if(!p.length)return"?";
  return (p[0][0]+(p.length>1?p[p.length-1][0]:"")).toUpperCase();
}
function hue(name){
  let h=0;
  for(const ch of String(name||""))h=(h*31+ch.charCodeAt(0))%360;
  return h;
}
function cardWidth(vw){
  /* Leave a gutter on the right so zoom controls do not cover the card. */
  if(vw<680)return Math.max(240,vw-88);
  return 312;
}
function maxCols(vw){
  if(vw<680)return 1;
  const w=cardWidth(vw);
  const usable=Math.max(w,vw-56);
  return Math.max(1,Math.min(3,Math.floor((usable+GAP)/(w+GAP))));
}
function estimateHeight(node,width){
  const textW=Math.max(120,width-96);
  const nameLines=Math.max(1,Math.ceil(node.name.length*7.2/textW));
  const person=node.head||node.kind==="seat"?54:0;
  const sub=node.sub?18:0;
  const level=node.level?16:0;
  return 36+nameLines*20+level+person+sub;
}

const ss=()=>new URL(location.href);

function Rs({domain:a,tools:Y}){
  const h=ys(a),{date:C}=Ns(),[y,G]=d.useState({}),[m,H]=d.useState(new Set),[g,B]=d.useState(new Set),[A,D]=d.useState({}),[k,S]=d.useState([h.root]),[r,w]=d.useState(null),[P,l]=d.useState([]),[u,z]=d.useState(!1),[W,ce]=d.useState(0),[fe,as]=d.useState({}),[Pe,je]=d.useState(""),[vw,setVw]=d.useState(()=>typeof innerWidth==="number"?innerWidth:1200);
  const Z=d.useRef(y);Z.current=y;
  d.useEffect(()=>(es("chart",!0),()=>es("chart",!1)),[]);
  d.useEffect(()=>{
    const onR=()=>setVw(innerWidth);
    window.addEventListener("resize",onR);
    return()=>window.removeEventListener("resize",onR);
  },[]);
  const L=d.useCallback(async s=>{
    if(Z.current[s.id])return Z.current[s.id];
    if(!s.kids)return[];
    B(t=>new Set(t).add(s.id));
    try{
      const t=await s.kids();
      return Z.current={...Z.current,[s.id]:t},G(n=>({...n,[s.id]:t})),t;
    }catch(t){return je(String(t)),[]}
    finally{B(t=>{const n=new Set(t);return n.delete(s.id),n})}
  },[]);
  const Re=s=>(y[s.id]??[]).filter(t=>{
    var n,c;
    return t.kind==="seat"?!((n=t.holders)!=null&&n.some(i=>i.start||i.end))||!!Ye(t,C)||!((c=t.holders)!=null&&c.length):Ms(t.start,t.end,C);
  });
  const Fe=d.useCallback(async(s,t=h.root)=>{
    let n=t;const c=[t],i=[t.id];
    e:for(const j of s.slice(s[0]===t.id?1:0)){
      const $=await $s(await L(n),j);
      if(!$)break;
      for(const b of $){
        const F=await L(n),o=F.findIndex(p=>p.id===b.id);
        if(o<0)break e;
        D(p=>({...p,[n.id]:Math.max(p[n.id]??le,o+1)})),n=F[o],c.push(n),i.push(n.id);
      }
    }
    return H(j=>{const $=new Set(j);return i.slice(0,-1).forEach(b=>$.add(b)),$}),c;
  },[L,h]);
  const _=(s,t,n=!0)=>{
    w(s),l(t),n&&z(!0);
    const c=ss();c.searchParams.set("node",s.id),history.replaceState(history.state,"",c);
  };
  d.useEffect(()=>{(async()=>{
    S([h.root]),w(null),z(!1);
    const s=new Set([h.root.id]),t=await L(h.root);
    if(t.length<=4&&t.forEach(c=>s.add(c.id)),a==="politics"){
      s.add("br-executive"),s.add("ctl-president");
      const c=t.find(i=>i.id==="br-executive");
      if(c){const i=await L(c);i[0]&&await L(i[0])}
    }else for(const c of t.slice(0,4))t.length<=4&&await L(c);
    H(s);
    const n=ss().searchParams.get("node");
    if(n&&n!==h.root.id){
      const c=h.pathTo?await h.pathTo(n):null;
      if(c){const i=await Fe(c),j=i[i.length-1];j.id===n&&(_(j,i),ie(n))}
    }
  })()},[a]);
  const Q=k[k.length-1];
  const width=cardWidth(vw),cols=maxCols(vw);
  const {placed:q,segs:ns,bounds:x}=d.useMemo(()=>{
    const placed=[],segs=[];
    const heightOf=o=>fe[o.id]??estimateHeight(o,width);
    const visible=(o,depth)=>{
      if(!m.has(o.id)||W&&depth>=W)return[];
      const all=Re(o).slice(0,xe);
      const shown=Math.min(xe,A[o.id]??le);
      const slice=all.slice(0,shown);
      if(all.length>shown)slice.push({id:`${o.id}::more`,name:`Show ${Math.min(le,all.length-shown)} more of ${(all.length-shown).toLocaleString()} remaining`,kind:"group"});
      return slice;
    };
    const build=(node,depth)=>{
      const kids=visible(node,depth).map(k=>build(k,depth+1));
      const hgt=heightOf(node);
      if(!kids.length)return{node,h:hgt,w:width,rows:[],totalH:hgt};
      const rows=[];
      let row=[],rowW=0;
      const limit=Math.max(width,cols*width+(cols-1)*GAP);
      for(const kid of kids){
        const next=row.length?rowW+GAP+kid.w:kid.w;
        if(row.length&&(row.length>=cols||next>limit)){rows.push(row);row=[];rowW=0}
        row.push(kid);
        rowW=row.length===1?kid.w:rowW+GAP+kid.w;
      }
      if(row.length)rows.push(row);
      const w=Math.max(width,...rows.map(r=>r.reduce((s,c,i)=>s+(i?GAP:0)+c.w,0)));
      let y=hgt+VGAP,totalH=hgt;
      const placedRows=rows.map(r=>{
        const rw=r.reduce((s,c,i)=>s+(i?GAP:0)+c.w,0);
        const rowH=Math.max(...r.map(c=>c.totalH));
        const item={y,rw,rowH,items:r};
        y+=rowH+ROWGAP;
        totalH=y-ROWGAP;
        return item;
      });
      return{node,h:hgt,w,rows:placedRows,totalH};
    };
    const assign=(box,left,top,parent)=>{
      const rec={n:box.node.kind==="seat"&&!box.node.seal&&parent?.n.seal?{...box.node,seal:parent.n.seal}:box.node,x:left+box.w/2,y:top,h:box.h,parent,key:(parent?parent.key+"/":"")+box.node.id,depth:parent?parent.depth+1:0};
      placed.push(rec);
      for(const row of box.rows){
        let xCursor=rec.x-row.rw/2;
        const busY=top+row.y-VGAP/2;
        const childRecs=[];
        for(const kid of row.items){
          childRecs.push(assign(kid,xCursor,top+row.y,rec));
          xCursor+=kid.w+GAP;
        }
        const xs=childRecs.map(c=>c.x);
        const leftX=Math.min(rec.x,...xs),rightX=Math.max(rec.x,...xs);
        segs.push(`M${rec.x},${top+box.h} V${busY}`);
        if(xs.length)segs.push(`M${leftX},${busY} H${rightX}`);
        for(const c of childRecs)segs.push(`M${c.x},${busY} V${c.y}`);
      }
      return rec;
    };
    const rootBox=build(Q,0);
    assign(rootBox,0,0,void 0);
    if(!placed.length)return{placed,segs,bounds:{minX:0,maxX:width,minY:0,maxY:80}};
    const bounds={minX:Math.min(...placed.map(o=>o.x-width/2)),maxX:Math.max(...placed.map(o=>o.x+width/2)),minY:0,maxY:Math.max(...placed.map(o=>o.y+o.h))};
    return{placed,segs,bounds};
  },[Q,m,y,A,C,fe,W,vw,width,cols]);

  const pe=d.useRef(new Map);
  d.useLayoutEffect(()=>{
    const s={};let t=!1;
    pe.current.forEach((n,c)=>{
      const i=n.offsetHeight;
      i&&Math.abs((fe[c]??-1)-i)>1&&(s[c]=i,t=!0);
    });
    t&&as(n=>({...n,...s}));
  });
  const Te=d.useRef(null),[Ue,ls]=d.useState(130);
  d.useLayoutEffect(()=>{
    const s=Te.current;if(!s)return;
    const t=()=>ls(Math.ceil(s.offsetTop+s.offsetHeight+12));
    t();
    const n=new ResizeObserver(t);
    return n.observe(s),()=>n.disconnect();
  },[]);
  const J=d.useRef(null),[f,K]=d.useState({x:0,y:0,k:1}),[ge,ie]=d.useState(null);
  const be=()=>{
    var i;
    const s=(i=J.current)==null?void 0:i.getBoundingClientRect();
    const t=(s?.width)??innerWidth,n=(s?.height)??innerHeight,c=u&&t>900?420:0;
    return{W0:t,H0:n-Ue,side:c};
  };
  const Be=()=>{
    const{W0:s,side:n}=be();
    const avail=Math.max(width,s-n);
    const chartW=x.maxX-x.minX;
    const mid=(x.minX+x.maxX)/2;
    const narrow=vw<680;
    K({k:1,x:narrow?12-x.minX:(chartW+48<=avail?(s-n)/2-mid:20-x.minX),y:12});
  };
  const cs=s=>{
    const{W0:t,side:c}=be();
    K(()=>({k:1,x:(t-c)/2-s.x,y:Math.max(12,36)}));
  };
  const R=d.useRef("");
  d.useEffect(()=>{
    if(ge){const t=q.find(n=>n.n.id===ge);t&&(cs(t),ie(null));return}
    const s=Q.id+":"+W+":"+vw;
    R.current!==s&&q.length>1&&(R.current=s,Be());
  },[q,ge,vw]);
  const ve=d.useRef(null);
  const is=s=>{s.target.closest("button,input,select,a,.oc-panel,.oc-mini")||(ve.current={x:s.clientX,y:s.clientY,vx:f.x,vy:f.y})};
  const rs=s=>{const t=ve.current;t&&K(n=>({...n,x:t.vx+s.clientX-t.x,y:t.vy+s.clientY-t.y}))};
  const Ae=()=>{ve.current=null};
  d.useEffect(()=>{
    const s=J.current;if(!s)return;
    const t=n=>{
      if(n.target.closest(".oc-panel,.oc-hits"))return;
      n.preventDefault();
      const c=s.getBoundingClientRect(),i=n.clientX-c.left,j=n.clientY-c.top;
      if(!n.ctrlKey&&Math.abs(n.deltaX)+Math.abs(n.deltaY)<60&&n.deltaMode===0&&!Number.isInteger(n.deltaY)){
        K(b=>({...b,x:b.x-n.deltaX,y:b.y-n.deltaY}));return;
      }
      const $=Math.exp(-n.deltaY*.0015);
      K(b=>{const F=Math.max(.8,Math.min(1.6,b.k*$));return{k:F,x:i-(i-b.x)*(F/b.k),y:j-(j-b.y)*(F/b.k)}});
    };
    return s.addEventListener("wheel",t,{passive:!1}),()=>s.removeEventListener("wheel",t);
  },[]);
  const De=s=>{
    const{W0:t,H0:n}=be();
    K(c=>{const i=Math.max(.8,Math.min(1.6,c.k*s));return{k:i,x:t/2-(t/2-c.x)*(i/c.k),y:n/2-(n/2-c.y)*(i/c.k)}});
  };
  const ke=s=>{const t=[];for(let n=s;n;n=n.parent)t.unshift(n.n);return[...k.slice(0,-1),...t]};
  const os=async s=>{
    const t=s.n;
    if(t.id.endsWith("::more")){const n=t.id.slice(0,-6);D(c=>({...c,[n]:(c[n]??le)+le}));return}
    if(_(t,ke(s),!t.kids),!!t.kids){
      if(m.has(t.id)&&s.parent){H(n=>{const c=new Set(n);return c.delete(t.id),c});return}
      await L(t),H(n=>new Set(n).add(t.id));
    }
  };
  const Ke=(s,t)=>{S(t.length?t:[h.root,s]),L(s),H(n=>new Set(n).add(s.id)),R.current=""};
  const ee=r?P:k;
  const ds=async s=>{
    const t=ee[s],n=k.findIndex(c=>c.id===t.id);
    n>=0&&(S(k.slice(0,n+1)),R.current=""),w(t),l(ee.slice(0,s+1)),ie(t.id);
  };
  const[se,hs]=d.useState(""),[Ve,ze]=d.useState([]),[us,we]=d.useState(!1);
  d.useEffect(()=>{
    if(se.trim().length<2){ze([]);return}
    let s=!0;const t=setTimeout(()=>h.search(se.trim()).then(n=>s&&ze(n)).catch(()=>{}),160);
    return()=>{s=!1,clearTimeout(t)};
  },[se,h]);
  const ms=async s=>{
    we(!1);
    const t=s.path?s.path[0]===h.root.id?s.path:[h.root.id,...s.path]:h.pathTo?await h.pathTo(s.id):null;
    if(S([h.root]),R.current=Q.id+":"+W,!t){Ke(s,[h.root,s]),_(s,[h.root,s]);return}
    const n=await Fe(t),c=n[n.length-1];
    c.id!==s.id&&je(`Could not reach “${s.name}” in the loaded chart (stopped at ${c.name}).`),_(c,n),ie(c.id);
  };
  const Ie=180,X=Math.min(Ie/Math.max(1,x.maxX-x.minX),110/Math.max(1,x.maxY-x.minY));
  const Ne=J.current?.clientWidth??innerWidth,ye=J.current?.clientHeight??innerHeight;
  const xs=s=>{
    const t=s.currentTarget.getBoundingClientRect();
    const n=(s.clientX-t.left)/X+x.minX,c=(s.clientY-t.top)/X;
    K(i=>({...i,x:Ne/2-n*i.k,y:ye/2-c*i.k}));
  };
  const Ge=new Set(ee.map(s=>s.id));
  const fs=-f.x/f.k-me,js=(Ne-f.x)/f.k+me,ps=-f.y/f.k-me,gs=(ye-f.y)/f.k+me;
  const bs=q.filter(s=>s.x+width/2>=fs&&s.x-width/2<=js&&s.y+s.h>=ps&&s.y<=gs);
  return e.jsxs("div",{className:"oc",style:{"--oc-top":`${Ue}px`,"--oc-card":`${width}px`},children:[
    e.jsxs("div",{className:"oc-bar glass",ref:Te,role:"toolbar","aria-label":"Org chart controls",children:[
      e.jsx("nav",{className:"oc-crumbs","aria-label":"Breadcrumbs",children:e.jsx("ol",{children:ee.map((s,t)=>e.jsxs("li",{children:[t>0&&e.jsx("span",{className:"sep","aria-hidden":"true",children:"›"}),t===ee.length-1?e.jsx("span",{"aria-current":"location",children:s.name}):e.jsx("button",{onClick:()=>ds(t),children:s.name})]},s.id+t))})}),
      e.jsxs("div",{className:"oc-tools",children:[
        Y,
        e.jsxs("div",{className:"oc-search",children:[
          e.jsx("input",{type:"search",value:se,onChange:s=>{hs(s.target.value),we(!0)},onFocus:()=>we(!0),placeholder:"Search any office, body or person…","aria-label":"Search the chart"}),
          us&&se.trim().length>=2&&e.jsx("ul",{className:"oc-hits glass",role:"listbox",children:Ve.length?Ve.map(s=>e.jsx("li",{children:e.jsxs("button",{onClick:()=>ms(s),children:[e.jsx("b",{children:s.name}),s.sub&&e.jsx("small",{children:s.sub})]})},s.id)):e.jsx("li",{className:"muted small",children:"No match in the sourced data."})})
        ]}),
        e.jsxs("label",{className:"oc-depth",children:["Levels ",e.jsxs("select",{value:W,onChange:s=>{ce(+s.target.value),R.current=""},"aria-label":"Show levels",children:[e.jsx("option",{value:0,children:"All open"}),[1,2,3,4,5].map(s=>e.jsx("option",{value:s,children:s},s))]})]}),
        k.length>1&&e.jsx("button",{onClick:()=>{S([h.root]),R.current=""},title:"Leave focus mode",children:"Exit focus"})
      ]})
    ]}),
    e.jsxs("div",{className:"oc-vp",ref:J,onPointerDown:is,onPointerMove:rs,onPointerUp:Ae,onPointerCancel:Ae,role:"application","aria-label":`${h.label} organization chart`,children:[
      e.jsxs("div",{className:"oc-world",style:{transform:`translate(${f.x}px, ${f.y}px) scale(${f.k})`},children:[
        e.jsx("svg",{className:"oc-links",style:{left:x.minX-40,top:-40,width:Math.max(1,x.maxX-x.minX+80),height:x.maxY+80},viewBox:`${x.minX-40} -40 ${Math.max(1,x.maxX-x.minX+80)} ${x.maxY+80}`,"aria-hidden":"true",children:ns.map((s,t)=>e.jsx("path",{d:s},t))}),
        bs.map(s=>e.jsx(Hs,{p:s,width,date:C,open:m.has(s.n.id),busy:g.has(s.n.id),selected:r?.id===s.n.id,onPath:Ge.has(s.n.id),count:y[s.n.id]?Re(s.n).length:s.n.count,isTop:!s.parent,canUp:!s.parent&&k.length>1,reg:t=>{t?pe.current.set(s.n.id,t):pe.current.delete(s.n.id)},onClick:()=>os(s),onInfo:()=>_(s.n,ke(s)),onFocus:()=>Ke(s.n,ke(s)),onUp:()=>{S(k.slice(0,-1)),R.current=""}},s.key))
      ]}),
      e.jsxs("div",{className:"oc-zoom glass",role:"group","aria-label":"Zoom",children:[
        e.jsx("button",{onClick:()=>De(1.15),"aria-label":"Zoom in",children:"+"}),
        e.jsx("button",{onClick:()=>De(1/1.15),"aria-label":"Zoom out",children:"−"}),
        e.jsx("button",{onClick:Be,"aria-label":"Fit chart to screen",title:"Fit",children:"⤢"})
      ]}),
      e.jsx("svg",{className:"oc-mini glass",width:Ie+12,height:122,onClick:xs,"aria-label":"Minimap: click to move there",children:e.jsxs("g",{transform:"translate(6,6)",children:[
        q.map(s=>e.jsx("rect",{x:(s.x-width/2-x.minX)*X,y:s.y*X,width:Math.max(1.5,width*X),height:Math.max(1.5,s.h*X),className:Ge.has(s.n.id)?"on":""},s.key)),
        e.jsx("rect",{className:"view",x:(-f.x/f.k-x.minX)*X,y:-f.y/f.k*X,width:Ne/f.k*X,height:ye/f.k*X})
      ]})}),
      Pe&&e.jsxs("div",{className:"oc-err glass",role:"status",children:[Pe," ",e.jsx("button",{onClick:()=>je(""),children:"OK"})]})
    ]}),
    u&&r&&e.jsx(Xs,{n:r,path:P,date:C,fmt:h.fmt,kids:y[r.id],onClose:()=>z(!1)})
  ]});
}

function Seal({n}){
  if(n.seal)return e.jsx("span",{className:"oc-seal",children:e.jsx("img",{src:n.seal.url,alt:"",loading:"lazy",decoding:"async"})});
  return e.jsx("span",{className:"oc-seal",children:e.jsx("span",{className:`oc-ico k-${n.kind||"org"}`,"aria-hidden":"true",children:ICONS[n.kind]||ICONS.org})});
}
function Avatar({name}){
  const shot=portraitOf(name);
  if(shot)return e.jsx("img",{className:"oc-av",src:shot.photoUrl,alt:shot.imageAlt||name,loading:"lazy"});
  const hueN=hue(name);
  return e.jsx("span",{className:"oc-ini",style:{background:`radial-gradient(120% 120% at 30% 20%, hsl(${hueN} 42% 42%), hsl(${(hueN+36)%360} 48% 16%))`},children:initials(name)});
}
function PersonLine({name,title,start,end,asOf,src}){
  if(!name)return null;
  const dates=(start||end)?`${start??"?"} – ${end??"present"}`:asOf?`as of ${asOf}`:null;
  return e.jsxs("div",{className:"oc-person",children:[
    e.jsx(Avatar,{name}),
    e.jsxs("span",{children:[
      title&&e.jsx("span",{className:"oc-htitle",children:title}),
      e.jsx("span",{className:"oc-hname",children:name}),
      dates&&e.jsx("span",{className:"oc-term",children:dates}),
      src&&e.jsx("a",{className:"oc-src",href:src,target:"_blank",rel:"noreferrer",onClick:ev=>ev.stopPropagation(),children:"source"})
    ]})
  ]});
}
function Hs({p:a,width,date:Y,open:h,busy:C,selected:y,onPath:G,count:m,isTop:H,canUp:g,reg:B,onClick:A,onInfo:D,onFocus:k,onUp:S}){
  const r=a.n,w=r.id.endsWith("::more");
  const holder=r.kind==="seat"?Ye(r,Y)??(r.holders&&!r.holders.some(ce=>ce.start||ce.end)?r.holders[0]:void 0):void 0;
  const head=r.kind==="seat"?holder?{title:"",name:holder.name,start:holder.start,end:holder.end,asOf:holder.asOf,src:holder.src}:null:r.head?{title:r.head.title,name:r.head.name,start:r.head.start,end:r.head.end,asOf:r.head.asOf,src:r.head.src}:null;
  return e.jsxs("div",{ref:B,className:`oc-card k-${r.kind}${h?" open":""}${y?" sel":""}${G?" path":""}${w?" more":""}${H?" top":""}`,"data-id":r.id,style:{transform:`translate(${a.x-width/2}px, ${a.y}px)`,width},children:[
    e.jsxs("button",{className:"oc-main",onClick:A,"aria-expanded":r.kids?h:void 0,children:[
      !w&&e.jsx(Seal,{n:r}),
      e.jsxs("span",{className:"oc-txt",children:[
        r.level&&!w&&e.jsx("span",{className:"oc-level",children:r.level}),
        e.jsx("span",{className:"oc-name",children:r.name}),
        !w&&r.holderCount&&r.holderCount>1?e.jsxs("span",{className:"oc-sub",children:[r.holderCount.toLocaleString()," ",r.collegial?"current members":"staff seats"]}):null,
        r.sub&&!w&&r.sub!==head?.name&&e.jsx("span",{className:"oc-sub",children:r.sub})
      ]})
    ]}),
    !w&&head&&e.jsx(PersonLine,{name:head.name,title:head.title,start:head.start,end:head.end,asOf:head.asOf,src:head.src}),
    !w&&!head&&r.kind==="seat"&&e.jsx("p",{className:"oc-vacant",children:"Vacant or no sourced holder at this date"}),
    !w&&e.jsxs("div",{className:"oc-foot",children:[
      r.kids?e.jsxs("span",{className:"oc-count",children:[C?"Loading…":h?"▾ ":"▸ ",!C&&(m?`${m.toLocaleString()} below`:h?"nothing below":"expand")]}):e.jsx("span",{className:"oc-count leaf",children:"no units below"}),
      e.jsxs("span",{className:"oc-acts",children:[
        g&&e.jsx("button",{onClick:S,title:"Up one level",children:"↑ Up"}),
        r.kids&&!H&&e.jsx("button",{onClick:k,title:"Focus: show only this subtree",children:"Focus"}),
        e.jsx("button",{onClick:D,title:"Details: holder, law, money, sources",children:"Details"})
      ]})
    ]})
  ]});
}
function Xs({n:a,path:Y,date:h,fmt:C,kids:y,onClose:G}){
  var A,D,k,S,r,w,P;
  const m=a.org,H=Ye(a,h)??a.holders?.[0],g=({u:l,t:u="source"})=>l?e.jsx("a",{className:"small",href:l,target:"_blank",rel:"noreferrer",children:u}):null,B=Y.length>1?Y[Y.length-2]:void 0;
  const headName=a.head?.name;
  const headShot=headName?portraitOf(headName):null;
  return e.jsxs("aside",{className:"oc-panel glass","aria-label":`Details: ${a.name}`,children:[
    e.jsxs("header",{children:[e.jsx(Seal,{n:a}),e.jsxs("div",{children:[e.jsx("span",{className:"oc-level",children:a.level??a.kind}),e.jsx("h3",{children:a.name})]}),e.jsx("button",{className:"x",onClick:G,"aria-label":"Close details",children:"×"})]}),
    e.jsxs("div",{className:"oc-pbody",children:[
      a.head&&e.jsxs("section",{children:[
        e.jsx("h4",{children:"Head"}),
        e.jsxs("p",{className:"oc-phead",children:[
          headShot?e.jsx("img",{src:headShot.photoUrl,alt:headShot.imageAlt||a.head.name}):e.jsx(Avatar,{name:a.head.name}),
          e.jsxs("span",{children:[
            e.jsx("b",{children:a.head.name}),e.jsx("br",{}),
            e.jsx("span",{className:"small",children:a.head.title}),
            a.head.start&&e.jsxs("span",{className:"small muted",children:[" · ",a.head.start,a.head.end?` – ${a.head.end}`:" – present"]}),
            a.head.asOf&&e.jsxs(e.Fragment,{children:[e.jsx("br",{}),e.jsxs("span",{className:`small${a.head.stale?" warn":" muted"}`,children:["Listed in the ",a.head.asOf]})]}),
            " ",e.jsx(g,{u:a.head.src})
          ]})
        ]})
      ]}),
      a.kind==="seat"&&e.jsxs("section",{children:[
        e.jsxs("h4",{children:["Holder",a.holders&&a.holders.length>1?"s":""]}),
        e.jsx("ul",{children:(a.holders??[]).map((l,u)=>e.jsxs("li",{className:l===H?"cur":"",children:[
          e.jsx(Avatar,{name:l.name})," ",l.name,
          (l.start||l.end)&&e.jsxs("span",{className:"small muted",children:[" · ",l.start??"?"," – ",l.end??"present"]}),
          " ",e.jsx(g,{u:l.src})
        ]},u))}),
        !a.holders?.length&&e.jsx("p",{className:"small muted",children:"No sourced holder."})
      ]}),
      e.jsxs("section",{children:[
        e.jsx("h4",{children:"Reports to"}),
        e.jsx("p",{children:B?B.name:"—"}),
        y&&e.jsxs(e.Fragment,{children:[e.jsx("h4",{children:"Controls"}),e.jsx("p",{children:y.length?`${y.length.toLocaleString()} units / seats directly below`:"Nothing below in the sourced data"})]})
      ]}),
      (A=m?.law)!=null&&A.length?e.jsxs("section",{children:[e.jsx("h4",{children:"§ Law"}),e.jsx("ul",{children:[...m.law].sort((l,u)=>l.date.localeCompare(u.date)).map((l,u)=>e.jsxs("li",{children:[e.jsx("span",{className:"small muted",children:l.date})," · ",l.href?e.jsx("a",{href:l.href,children:l.title}):l.title," ",e.jsx(g,{u:l.src})]},u))})]}):null,
      (D=m?.finance)!=null&&D.length?e.jsxs("section",{children:[e.jsx("h4",{children:"$ Money"}),e.jsx("ul",{children:m.finance.map((l,u)=>e.jsxs("li",{children:[l.metric,": ",e.jsx("b",{children:C(l.value,l.unit)}),l.asOf&&e.jsxs("span",{className:"small muted",children:[" (as of ",l.asOf,")"]})," ",e.jsx(g,{u:l.src})]},u))})]}):null,
      (k=a.links)!=null&&k.length?e.jsxs("section",{children:[e.jsx("h4",{children:"Official references"}),e.jsx("ul",{className:"small",children:a.links.map((l,u)=>e.jsx("li",{children:e.jsx("a",{href:l.url,target:"_blank",rel:"noreferrer",children:l.label})},u))})]}):null,
      e.jsxs("section",{className:"small muted",children:[
        a.seal?e.jsxs(e.Fragment,{children:["Seal: ",a.seal.credit?e.jsxs(e.Fragment,{children:[e.jsx(g,{u:a.seal.credit.url,t:a.seal.credit.file??"Wikimedia Commons"})," · ",a.seal.credit.license]}):"public-domain U.S. government seal"]}):"No seal or logo on file.",
        a.src&&e.jsxs(e.Fragment,{children:[" · ",e.jsx(g,{u:a.src,t:"Source record"})]})
      ]}),
      (S=a.roster)!=null&&S.length?e.jsxs("section",{children:[e.jsxs("h4",{children:["Members (",a.roster.length,")"]}),e.jsx("ul",{children:a.roster.slice(0,xe).map((l,u)=>e.jsxs("li",{children:[l.title&&e.jsxs("span",{className:"small muted",children:[l.title,": "]}),e.jsx("b",{children:l.name})," ",e.jsx(g,{u:l.src})]},u))})]}):null,
      (r=a.council)!=null&&e.jsxs("section",{"data-council":!0,children:[
        e.jsxs("h4",{children:["Members · ",a.council.authority," ",e.jsx(g,{u:a.council.src,t:"text"})]}),
        e.jsx("ul",{children:a.council.members.map((l,u)=>e.jsxs("li",{children:[e.jsxs("span",{className:"small muted",children:[l.seat,!l.voting&&" (non-voting)",": "]}),l.name?e.jsx("b",{children:l.name}):e.jsx("span",{className:"small muted",children:"holder not in source data"})," ",e.jsx(g,{u:l.src})]},u))})
      ]}),
      (w=m?.positions)!=null&&w.length>1&&e.jsxs("section",{children:[e.jsx("h4",{children:"Seats on record"}),e.jsx("ul",{children:m.positions.slice(0,40).map((l,u)=>e.jsxs("li",{children:[l.title,": ",e.jsx("b",{children:l.name})," ",e.jsx(g,{u:l.src})]},u))})]}),
      (P=a.rosterEnded)!=null&&P.length?e.jsxs("section",{"data-ended":!0,children:[e.jsxs("h4",{children:["No longer serving (",a.rosterEnded.length,")"]}),e.jsx("ul",{children:a.rosterEnded.map((l,u)=>e.jsxs("li",{className:"small muted",children:[l.title&&`${l.title}: `,l.name,l.end?` · ended ${l.end}`:""," ",e.jsx(g,{u:l.endSrc})]},u))})]}):null
    ]})
  ]});
}
export{Rs as default};

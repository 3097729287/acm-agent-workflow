// Adapt legacy Typora formula boundaries for CommonMark, only while displaying.
// Code, escaped dollars, and unmatched delimiters remain unchanged.
function escaped(text,index){let slashes=0;for(let i=index-1;i>=0&&text[i]==='\\';i--)slashes++;return slashes%2===1}

function prose(text){
  let out='',i=0,inline=false;
  while(i<text.length){
    if(text[i]==='`'){
      let end=i;while(text[end]==='`')end++;
      const marker=text.slice(i,end),close=text.indexOf(marker,end);
      if(close>=0){out+=text.slice(i,close+marker.length);i=close+marker.length;continue}
    }
    if(text[i]!=='$'||escaped(text,i)){out+=text[i++];continue}
    let end=i;while(text[end]==='$')end++;
    const count=end-i;
    if(count===1){
      // Avoid interpreting an unmatched currency/dollar as an inline opener.
      const lineEnd=text.indexOf('\n',end),limit=lineEnd<0?text.length:lineEnd;
      let closes=false;
      for(let j=end;j<limit;j++)if(text[j]==='$'&&!escaped(text,j)){closes=true;break}
      if(inline||closes)inline=!inline;
      out+='$';i=end;continue;
    }
    if(count!==2){out+=text.slice(i,end);i=end;continue}
    if(inline){
      // Adjacent inline formulas: $a$$b$ -> $a$ $b$.
      out+='$ $';i=end;continue;
    }
    let close=-1;
    for(let j=end;j<text.length-1;j++){
      if(text[j]==='`'){
        let k=j;while(text[k]==='`')k++;
        const marker=text.slice(j,k),finish=text.indexOf(marker,k);
        if(finish>=0){j=finish+marker.length-1;continue}
      }
      if(text.slice(j,j+2)==='$$'&&!escaped(text,j)&&text[j+2]!=='$') {close=j;break}
    }
    if(close<0){out+='$$';i=end;continue}
    const body=text.slice(end,close);
    if(!body.includes('\n')){out+=text.slice(i,close+2);i=close+2;continue}
    // Multiline display math needs both delimiter runs on their own lines.
    const prefix=out.slice(out.lastIndexOf('\n')+1);
    const suffix=text.slice(close+2).split('\n',1)[0];
    if(prefix.trim())out+='\n\n';
    out+='$$'+(body.startsWith('\n')?'':'\n')+body+(body.endsWith('\n')?'':'\n')+'$$';
    if(suffix.trim())out+='\n\n';
    i=close+2;
  }
  return out;
}

export function normalizeMarkdown(text=''){
  const lines=String(text).split(/(?<=\n)/),parts=[];
  let pending='',fence=null;
  const flush=()=>{if(pending){parts.push(prose(pending));pending=''}};
  for(const line of lines){
    const match=line.match(/^ {0,3}(`{3,}|~{3,})/);
    if(fence){
      parts.push(line);
      if(match&&match[1][0]===fence.character&&match[1].length>=fence.length&&line.slice(match[0].length).trim()==='')fence=null;
    }else if(match){flush();fence={character:match[1][0],length:match[1].length};parts.push(line)}
    else pending+=line;
  }
  flush();
  return parts.join('');
}

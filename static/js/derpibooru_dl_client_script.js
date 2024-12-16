// ==UserScript==
// @name        derpibooru_dl_client_script
// @namespace   Violentmonkey Scripts
// @match       https://derpibooru.org/
// @match       https://derpibooru.org/images*
// @match       https://derpibooru.org/search
// @match       https://derpibooru.org/tags/*
// @match       https://twibooru.org/*
// @match       https://ponybooru.org/
// @match       https://ponybooru.org/images*
// @match       https://ponybooru.org/search
// @match       https://ponybooru.org/tags/*
// @match       https://furbooru.org/
// @match       https://furbooru.org/images*
// @match       https://furbooru.org/search
// @match       https://furbooru.org/tags/*
// @match       https://tantabus.ai/
// @match       https://tantabus.ai/images*
// @match       https://tantabus.ai/search
// @match       https://tantabus.ai/tags/*
// @match       https://e621.net/popular
// @match       https://e621.net/favorites
// @match       https://e621.net/posts
// @match       https://e621.net/posts/*
// @connect     localhost:5757
// @grant       GM.xmlHttpRequest
// @version     1.4.1
// @author      mfg637
// @description 12.03.2021, 13:25:40
// ==/UserScript==

var url_head = 'http://localhost:5757';

waiting_dl_button = null

function get_url(){
  const hostname = window.location.hostname;
  let url = url_head;
  switch (hostname) {
    case "derpibooru.org":
      break;
    case 'twibooru.org':
      url = url_head + "/twibooru";
      break;
    case "ponybooru.org":
      url = url_head + "/ponybooru";
      break;
    case "e621.net":
      url = url_head + "/e621";
      break;
    case "furbooru.org":
      url = url_head + "/furbooru";
      break;
    case "tantabus.ai":
      url = url_head + "/tantabus";
      break;
    default:
      alert(`Implementation error: site ${hostname} is not implemented! (line 56)`)
      break;
  };
  return url
}

function dl_button_click_handler(event){
  console.log(this.data);
  console.log(JSON.stringify(this.data));

  const url = get_url();
    
  GM.xmlHttpRequest({
    method: "POST",
    data: JSON.stringify(this.data),
    url: url,
    onload: function(response) {
      if (response.responseText === "OK"){
        event.target.style.backgroundColor = "green";
        event.target.style.color = 'white';
        console.log(response.responseText);
      }else
        alert(response.responseText);
    }
  });
  return false;
}

function button_placer_default(dl_button, image_wrapper){
  const hostname = window.location.hostname;
  dl_button.innerText='dl';
  const url = get_url();
  dl_button.href = url;
  switch (hostname) {
    case "ponybooru.org":
    case "furbooru.org":
    case "tantabus.ai":
    case "derpibooru.org":
      image_wrapper.getElementsByClassName('media-box__header')[0].appendChild(dl_button);
      break;
    case 'twibooru.org':
      image_wrapper.getElementsByClassName('media-box__header')[0].getElementsByTagName('form')[0].appendChild(dl_button);
      break;
    case "e621.net":
      image_wrapper.appendChild(dl_button);
      break;
    default:
      alert(`Implementation error: site ${hostname} is not implemented! (line 102)`)
      break;
  }
}

function button_placer_show_image(dl_button, unused_arg){
  dl_button.innerText='DDL';
  const url = get_url();
  dl_button.href = url;
  document.getElementsByClassName('image-metabar')[0].appendChild(dl_button);
}

function image_handler(data_wrapper, button_placer, bp_arg=null){
  let raw_data = data_wrapper.dataset, data = {};
  for (let key in raw_data){data[key]=raw_data[key];}
  data.representations=JSON.parse(data.uris);
  delete data.uris;
  let dl_button = document.createElement('a');
  dl_button.data = data;
  dl_button.onclick = dl_button_click_handler;
  dl_button.style.fontWeight = 'Bold';
  button_placer(dl_button, bp_arg);
}


function e621_image_handler(data_wrapper, button_placer, placing_place){
  let raw_data = data_wrapper.dataset, data = {};
  for (let key in raw_data){data[key]=raw_data[key];}
  let dl_button = document.createElement('a');
  dl_button.data = data;
  dl_button.onclick = dl_button_click_handler;
  dl_button.style.fontWeight = 'Bold';
  dl_button.style.marginLeft = "0.5em";
  button_placer(dl_button, placing_place);
}


const hostname = window.location.hostname;
if  (
      (hostname === "derpibooru.org") ||
      (hostname === 'twibooru.org') ||
      (hostname === "ponybooru.org") ||
      (hostname === "furbooru.org") ||
      (hostname === "tantabus.ai")
    )
{
  image_wrappers = document.getElementsByClassName('media-box');
  if (image_wrappers.length > 0)
    for (let i in image_wrappers) {
      if (!(image_wrappers[i] instanceof Element)) {
        continue
      }
      data_wrapper = image_wrappers[i].getElementsByClassName('image-container')[0];
      image_handler(data_wrapper, button_placer_default, image_wrappers[i]);
    }
  else {
    image_wrappers = document.getElementsByClassName('image-show-container');
    if (image_wrappers.length > 0) {
      data_wrapper = image_wrappers[0];
      image_handler(data_wrapper, button_placer_show_image);
    }
  }
}else if (hostname === "e621.net"){
  image_wrappers = document.getElementsByClassName('thumbnail');
  if (image_wrappers.length > 0) {
    for (let i in image_wrappers) {
      if (!(image_wrappers[i] instanceof Element)) {
        continue
      }
      e621_image_handler(
          image_wrappers[i],
          button_placer_default,
          image_wrappers[i].childNodes[1]
      );
    }
  }
  image_wrapper = document.getElementById('image-container');
  if (image_wrapper !== null) {
    e621_image_handler(
      image_wrapper,
      button_placer_default,
      document.getElementById("image-extra-controls")
    )
  }
}

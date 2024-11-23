function customSwal(text = "Success!", options = {
    animationTime: '1s',
    animatiomType: 'ease',
    hideDelay: '3500',
    type: 'success',
    html: false
}) { // animationTime = '1s', animatiomType = 'ease', hideDelay = 1500
    console.log(arguments)
    if ((options.type || "success") == "success") {
        $(".customSwal__icon").html('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><path d="M256 512c141.4 0 256-114.6 256-256S397.4 0 256 0S0 114.6 0 256S114.6 512 256 512zM369 209L241 337c-9.4 9.4-24.6 9.4-33.9 0l-64-64c-9.4-9.4-9.4-24.6 0-33.9s24.6-9.4 33.9 0l47 47L335 175c9.4-9.4 24.6-9.4 33.9 0s9.4 24.6 0 33.9z"/></svg>')
        $(".customSwal").css('background', '#cceecb')
        $(".customSwal__icon path").css('fill', '#76c574')
        $(".customSwal__text").css('color', '#656565')
        $(".customSwal__icon svg").css('height', '60px')
    } else if (options.type == 'error') {
        $(".customSwal__icon").html('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 512"><path d="M310.6 150.6c12.5-12.5 12.5-32.8 0-45.3s-32.8-12.5-45.3 0L160 210.7 54.6 105.4c-12.5-12.5-32.8-12.5-45.3 0s-12.5 32.8 0 45.3L114.7 256 9.4 361.4c-12.5 12.5-12.5 32.8 0 45.3s32.8 12.5 45.3 0L160 301.3 265.4 406.6c12.5 12.5 32.8 12.5 45.3 0s12.5-32.8 0-45.3L205.3 256 310.6 150.6z"/></svg>')
        $(".customSwal").css('background', '#ffa7a7')
        $(".customSwal__icon path").css('fill', '#e36767')
        $(".customSwal__text").css('color', '#fcfcfc')
        $(".customSwal__icon svg").css('height', '60px')
    } else if (options.type == 'warning') {
        $(".customSwal__icon").html('<svg height="" viewBox="0 0 512 512" width="" xmlns="http://www.w3.org/2000/svg"><path d="M85.57,446.25H426.43a32,32,0,0,0,28.17-47.17L284.18,82.58c-12.09-22.44-44.27-22.44-56.36,0L57.4,399.08A32,32,0,0,0,85.57,446.25Z" style="fill:none;stroke-linecap:round;stroke-linejoin:round;stroke-width:32px"></path><path d="M250.26,195.39l5.74,122,5.73-121.95a5.74,5.74,0,0,0-5.79-6h0A5.74,5.74,0,0,0,250.26,195.39Z" style="fill:none;stroke-linecap:round;stroke-linejoin:round;stroke-width:32px"></path><path d="M256,397.25a20,20,0,1,1,20-20A20,20,0,0,1,256,397.25Z"></path></svg>')
        $(".customSwal").css('background', '#f8fbcb')
        $(".customSwal__icon path").css('fill', '#c8ce76')
        $($(".customSwal__icon path").get(0)).css('fill', 'none')
        $(".customSwal__icon path").css('stroke', '#c8ce76')
        $(".customSwal__text").css('color', '#656565')
        $(".customSwal__icon svg").css('height', '60px')
    } else {
        return console.error(`type ${options.type} does not exsist.\navailable types:\n'success', 'error', 'warning'` )
    }
    $(".customSwal").css('transition', `transform ${options.animationTime || '1s'} ${options.animatiomType || 'ease'}`)
    $(".customSwal").addClass("active")
    options.html || false ? $(".customSwal__text").html(text) :  $(".customSwal__text").text(text)
    let removeClassActive = setTimeout(function () {
        $(".customSwal").removeClass("active")
    }, options.hideDelay || '3500')
    $(".customSwal").click(event => {
        $(event.target.closest('.customSwal')).removeClass("active")
        clearTimeout(removeClassActive)
    })
}
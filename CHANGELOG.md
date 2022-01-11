## IN_CG_Accessibility_Checker
##### Project uses [Version](https://kb.epam.com/display/EPMACCHK/CHANGELOG.md)


## [Unreleased]()


### 1.0.4 - 2020-04-28 
[@Aleksandr_Perelygin](https://git.epam.com/Aleksandr_Perelygin)

#### Added
- Create - element_wrapper
- Create - base_func for edit box

#### Changed
- Fixed - element_rect
- Fixed - test_audio - Ensures that auto playing audio content can be stopped
- Fixed - test_pointer - Ensures that For functionality that can be operated using a single pointer, at least one of the 4 points set by the WCAG is true
- Fixed - test_labels - Ensures that found edit boxes has proper label
- Fixed - test_alerts_edit_box - Ensures that after an error in the input field, an element with an error is identified, and the error is described to the user in a text notification
- Fixed - test_working - Ensures that found edit boxes was working
- Fixed - test_flickering - Ensures that page don't have flickering elements
- Fixed - test_size_pict - Ensures that flickering images on page have size not more than 25% off size page
- Fixed - test_tables_struct - Ensures that all elements that have a table structure are designed according to WCAG


- Deleted test_resizable - Ensures that found edit boxes not resizable (DEPRECATED)


### 1.0.3 - 2020-04-27 
[@Nikolay_Ryabichko](https://git.epam.com/Nikolay_Ryabichko)

#### Changed
- Commented - test_menubar_buttons (disabled test) - Ensure that menubar buttons have correct role
- Commented - test_menubar_listholder (disabled test) - Ensure that menubar listholders have correct role
- Commented - test_menubar_navigation (disabled test) - Ensure that menubar have correct navigation mechanism


- Fixed - test_buttons_role - Ensure that buttons have appropriate roles (Changes mainly in the dependent test)
- Fixed - test_checkbox - Ensure that checkboxes have appropriate role
- Fixed - test_focus_combobox - Ensures that navigation mechanism in combobox is accessible
- Fixed - test_menu_listholder - Ensure that menu listholders have correct role
- Fixed - test_menu_listitems - Ensure that menu listitems have correct role
- Fixed - test_selector_button - Ensure that selector button have correct role
- Fixed - test_selector_listholder - Ensure that selector listholder have correct role
- Fixed - test_selector_listitems - Ensure that selector list items have correct role


- Disabled - test_menu_nav_loop - Ensure that navigation focus order in dropdown menu is looped
- Disabled - test_menu_nav_moving - Ensure that dropdown menu support keyboard navigation mechanism


### 1.0.2 - 2020-04-24 
[@anna_isaeva](https://git.epam.com/anna_isaeva)

#### Changed
- Fixed - test_search_methods - Ensures that web page has several ways to navigate
- Fixed - test_shortcut_list - Ensures that custom implemented lists have 'role=list' and items have 'role=listitem' (United with deleted test_shortcut_list_item)
- Fixed - test_image_with_text_mismatch - Ensures that img element with text has text description that matches the text in the this image
- Fixed - test_header - Ensures that h1-h6 elements well express the semantic content of the texts relating to them
- Fixed - test_link_information_purposeUI - Ensures that a elements has description of which is handing semantic content resource far refers a
- Fixed - test_links_information - Ensures that a elements have text explaining their purpose


- Delete - test_shortcut_list_item - Ensures that items in custom implemented list have 'role=listitem' attribute set


### 1.0.1 - 2020-04-17 
[@Aleksandr_Perelygin](https://git.epam.com/Aleksandr_Perelygin)

#### Changed
- Fixed - screenshot - new features added described in [KB](https://kb.epam.com/display/EPMACCHK/Accessibility+Testing+Framework)
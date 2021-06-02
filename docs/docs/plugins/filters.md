# Using filters

Filters are one of cutevariant's key features to select variants based on their properties.


First, if you don't see the filters editor plugin, this may be because it's hidden. To show it, toggle its visibility in the top toolbar, you can see it with the :material-filter: icon.

This is how the plugin looks like when you have a blank project:

![Filters plugin](../images/filters.png)

As you can see, the plugin is just a tree view with one root item. This item represents the root of the filter, which means that everything you will add as child items will be chained with `AND` statements. Among these child statements, you can in turn add `OR` or `AND` statements.

The following example:

![Filters example](../images/filters_example.png)

will select variants where `ref = A AND ref = T`

You can add as much nesting as you wish, so the following will work as well 

!!! info
    This example selects base transversions, see [wikipedia]().

If you'd like to change any `AND` statement into an `OR`, you can do this by simply double-cliking the item and selecting the logical operator.

Once you're happy with the filter you just set, you can simply hit the <kbd>:material-check:Apply</kbd> button on the right.

If you'd like to set the filter as a preset, you can do so by pressing <kbd>Save as preset</kbd> in the dropdown menu of the plugin.

[^1]: This is a general remark, the whole point of cutevariant is to narrow down a selection of variants, as much as you can, and with the maximum amount of information.
